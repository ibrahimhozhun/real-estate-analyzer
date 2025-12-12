"""Web scraper module for extracting real estate listing data.

This module provides a Scraper class that uses Selenium to automate
browser interactions and extract structured data from real estate websites.

The scraper implements a two-phase approach:
    Phase 1: Extract listing summaries from list-view pages (URLs, titles, prices)
    Phase 2: Extract detailed attributes from individual listing detail pages
"""

import os
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from random import randint
import time

from src.config import TARGET_DOMAIN
from .utils.error_handler import handle_scraping_exception
import pandas as pd


class Scraper:
    """A web scraper for extracting real estate data using Selenium.

    This class manages a Chrome WebDriver instance and provides methods to
    navigate to URLs and extract structured data from real estate listings.
    Implements context manager protocol for safe resource management.

    The scraper operates in two phases:
        1. List View Extraction: Quickly gathers URLs and basic info from search results
        2. Detail View Extraction: Deep scrapes individual listings for comprehensive data

    Attributes:
        driver (uc.Chrome): The patched Chrome WebDriver instance that mimics
            human browser fingerprints to avoid detection.

    Example:
        >>> with Scraper() as scraper:
        ...     df = scraper.scrape_multiple_pages(
        ...         base_url="https://example.com/listings?filter=...",
        ...         start=1,
        ...         stop=5
        ...     )
        ...     print(df.head())
    """

    def __init__(self):
        """Initialize the Scraper with a Chrome WebDriver instance."""
        options = uc.ChromeOptions()
        # options.add_argument('--headless')  # Keep headed for now to reduce detection risk
        self.driver = uc.Chrome(options=options)

    def __enter__(self):
        """Enter the context manager.

        Returns:
            Scraper: The scraper instance itself, allowing it to be used
                in a 'with' statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, ensuring the driver is closed.

        Guarantees cleanup of browser resources even if an exception occurs
        during scraping operations.

        Args:
            exc_type: The type of exception that occurred (if any).
            exc_val: The exception instance (if any).
            exc_tb: The exception traceback (if any).
        """
        self.close()

    def fetch(self, url: str, page_type: str):
        """Navigate the browser to the specified URL.

        Args:
            url (str): The target URL to load in the browser.
            page_type (str): This parameter used to detect which element that scraper should wait to load
                'list-view' for list view pages and 'detail-page' for listing detail page
        Note:
            This method waits for the page to load before returning.
        """
        self.driver.get(url)

        # Wait for the main content container to ensure the page is effectively loaded
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.list-view-content" if page_type == 'list-view' else "ul.adv-info-list li.spec-item"))
            )
        except TimeoutException:
            print(f"Warning: Timeout waiting for content at {url}")

    def _safe_find_text(self, parent_element, selector: str, default: str = None):
        """Safely find an element and return its text, handling NoSuchElementException.

        This is an internal helper method to reduce code duplication in the main
        extract method. It encapsulates the try-except logic for finding a
        single element's text.

        Args:
            parent_element: The Selenium element to search within.
            selector (str): The CSS selector for the target child element.
            default (str, optional): The value to return if the element is not found.
                                    Defaults to None.

        Returns:
            str or None: The text content of the found element, or the default value.
        """
        try:
            return parent_element.find_element(By.CSS_SELECTOR, selector).text
        except NoSuchElementException:
            return default

    def extract(self):
        """[Phase 1] Extract listing summaries from the current list-view page.

        This is the first phase of the two-phase scraping process. It quickly
        extracts the basic, reliably available data from each listing on a
        search results (list view) page, most importantly the URL to the
        listing's detail page.

        The data extracted here includes:
            - listing_id: The listing's id
            - title: The listing's display name
            - price: The asking price (raw text, including currency)
            - location: The neighborhood or area
            - url: The hyperlink to the listing's detail page

        Returns:
            pd.DataFrame: A DataFrame containing listing summaries with columns:
                ['listing_id', 'title', 'price', 'location', 'url']. Returns an empty
                DataFrame if the extraction fails, allowing graceful handling
                in the calling code.
        """
        try:
            # Initialize list to collect data from each listing (converted to DataFrame later )
            data = []
            # Locate all elements that contain listings
            listings = self.driver.find_elements(
                By.CSS_SELECTOR, "div.list-view-content")

            # Iterate through each listing container and extract basic info
            for listing in listings:
                try:
                    link_element = listing.find_element(
                        By.CSS_SELECTOR, "a.card-link")
                    url = link_element.get_attribute("href")
                except NoSuchElementException:
                    url = None

                # Use the helper method to safely extract raw text for each field
                listing_data = {
                    "listing_id": url.split("/")[-1],
                    "title": self._safe_find_text(listing, "header.list-view-header > h3"),
                    "price": self._safe_find_text(listing, "span.list-view-price"),
                    "location": self._safe_find_text(listing, "span.list-view-location"),
                    "url": url
                }

                data.append(listing_data)

            # Convert collected data to DataFrame for analysis
            return pd.DataFrame(data)

        except Exception as e:
            # Delegate error handling to centralized error handler
            handle_scraping_exception(e)
            # Return empty DataFrame for consistency
            return pd.DataFrame()

    def extract_listing_details(self, url: str):
        """[Phase 2] Navigate to a listing's detail page and extract comprehensive attributes.

        This is the second phase of the two-phase scraping process. It navigates to an
        individual listing's detail page and performs a deep scrape of all available
        attributes, including features that are not displayed on the list view.

        The method uses a KEY_MAPPING dictionary to translate Turkish field labels
        (as displayed on real estate website) into standardized English database column names.
        This decoupling ensures that if the website's UI labels change, we only need to
        update the mapping table, not the entire extraction logic.

        The extraction process follows a three-step strategy:
            1. Find the field's label (raw_key in Turkish)
            2. Look up the English column name (db_key) in the mapping
            3. Extract the value using a chained fallback strategy:
                - First, try the primary CSS selector (.value-txt)
                - If that fails, try alternative selectors (e.g., 'a' tag for links)
                - If both fail, parse the raw text as a last resort

        Field-specific parsing:
            - m2_info: Split "Brüt / Net" into separate m2_gross and m2_net columns
            - is_furnished: Convert "Eşyalı" to boolean True, others to False

        Args:
            url (str): The full URL of the real estate listing's detail page.

        Returns:
            dict: A dictionary containing cleaned and standardized listing details.
                    Keys correspond to the database column names from KEY_MAPPING.
                    If a field is not found, it is simply omitted from the dictionary
                    (allowing None values to be handled during data cleaning).

        Note:
            - A random delay is applied after scraping each detail page
                to simulate human-like browsing behavior and avoid IP bans.
            - If an error occurs during extraction, it is logged via the centralized
                error handler, and the method returns whatever data was successfully
                extracted so far.
        """
        # Navigate to the detail page
        self.fetch(urljoin(TARGET_DOMAIN, url), page_type='detail-page')

        # Mapping Table: Website Label (Turkish) -> Database Column (English)
        # This mapping serves as the source of truth for field names.
        # If the website's UI labels change, only update this dictionary.
        KEY_MAPPING = {
            # --- Identity & Meta ---
            "İlan no": "listing_id",
            "Son Güncelleme": "last_updated",
            "İlan Durumu": "listing_type",

            # --- Physical Properties ---
            "Konut Tipi": "property_type",
            "Konut Şekli": "housing_form",

            # --- Dimensions & Rooms ---
            "Oda Sayısı": "room_count",
            "Banyo Sayısı": "bathroom_count",
            "Brüt / Net M2": "m2_info",

            # --- Floor Info (Critical for Apartments) ---
            "Kat Sayısı": "total_floors",
            "Bulunduğu Kat": "floor_location",

            # --- Utilities & Comfort ---
            "Isınma Tipi": "heating_type",
            "Eşya Durumu": "is_furnished",
            "Cephe": "facade",

            # --- Financial & Legal ---
            "Bina Yaşı": "building_age",
            "Krediye Uygunluk": "credit_eligibility",
            "Krediye Uygunlu...": "credit_eligibility",
            "Tapu Durumu": "title_deed_status",
            "Takas": "swap_available",
        }

        # Initialize dictionary to store extracted details
        listing_details = {}

        try:
            # Locate all specification item containers on the detail page
            # Each li.spec-item contains a single attribute (label + value pair)
            spec_items = self.driver.find_elements(
                By.CSS_SELECTOR, "ul.adv-info-list li.spec-item")

            for item in spec_items:
                # --- Step A: Extract and validate the field label ---
                # The .txt class contains the Turkish label (e.g., "Oda Sayısı")
                raw_key = self._safe_find_text(item, ".txt")

                # Validation: If label is missing or not in our map, skip this item
                if not raw_key or raw_key not in KEY_MAPPING:
                    continue

                # Look up the English column name for this field
                db_key = KEY_MAPPING[raw_key]

                # --- Step B: Extract the field value using a chained fallback strategy ---
                # 1. Primary selector: .value-txt (the most common format)
                # 2. Fallback selector: 'a' tag (used for link-based values)
                # The 'or' operator returns the first non-None value
                value = self._safe_find_text(
                    item, ".value-txt") or self._safe_find_text(item, "a")

                # 3. Final fallback: If both selectors fail, parse the item's raw text
                # This is a last-resort strategy for unusual HTML structures
                if not value:
                    # Remove the label from the text to isolate the value
                    full_text = item.text.strip()
                    if full_text:
                        value = full_text.replace(raw_key, "").strip()

                # --- Step C: Parsing & Cleaning ---

                # Handle m2_info: Split "Brüt / Net" into two separate columns
                if db_key == "m2_info" and value and "/" in value:
                    parts = value.split("/")
                    if len(parts) == 2:
                        listing_details["m2_gross"] = parts[0].replace(
                            "m2", "").strip()
                        listing_details["m2_net"] = parts[1].replace(
                            "m2", "").strip()
                    continue

                # Handle is_furnished: Convert Turkish text to boolean
                if db_key == "is_furnished" and value:
                    # "Eşyalı" means furnished; anything else is unfurnished
                    value = True if "Eşyalı" == value else False
                    # Important: Always assign this field (even if False) to ensure consistency
                    listing_details[db_key] = value
                    continue

                # For all other fields: Store the value as-is (raw text)
                # Cleaning (e.g., converting "3" to integer) is handled in Phase 3
                if value:
                    listing_details[db_key] = value

        except Exception as e:
            # Log the error for debugging, but don't crash the entire scrape
            print(f"Error extracting details for {url}")
            handle_scraping_exception(e)

        return listing_details

    def scrape_multiple_pages(self, base_url: str, start: int = 1, stop: int = 5):
        """Orchestrates the two-phase scraping process across multiple paginated pages.

        This is the main orchestrator method that drives the entire scraping workflow:
            Phase 1: Discover listings by scraping list-view pages
            Phase 2: Extract detailed attributes for each discovered listing

        The method loops through a range of page numbers, calling extract() for each
        list-view page to get a set of listing URLs, then iterates through those URLs
        and calls extract_listing_details() to perform deep scraping.

        Results from all pages are aggregated into a single pandas DataFrame,
        which is stored in a csv file and then returned to the caller.

        Args:
            base_url (str): The base URL for the listing search, including query
                            parameters. New page numbers are appended with '&page={n}'.
                            Example: "https://site.com/listings?filter=...&sortBy=..."
            start (int): The starting page number (inclusive). Default: 1.
            stop (int): The page number to stop before (exclusive). For example,
                        stop=5 will scrape pages 1, 2, 3, and 4.
                        Default: 5.

        Returns:
            pd.DataFrame: A single DataFrame containing all scraped listings with
                            both summary data (from Phase 1) and detailed data (from Phase 2).
                            Returns an empty DataFrame if no data was collected.

        Note:
            - The method automatically stops if it encounters an empty page,
                indicating there are no more listings to scrape.
            - Random delays are applied between page requests
                to be respectful to the target server and avoid IP bans.
            - The merging of Phase 1 and Phase 2 data uses Python's dictionary unpacking:
              full_listing_data = {**listing, **details}
                This combines summary and detail data into a single record.
            - The data from every page is stored in seperate csv files
        """
        # Initialize list to collect all scraped records from all pages
        all_data = []
        # Initialize list to store csv file's names
        batch_files = []

        # Iterate through the specified page range
        for index in range(start, stop):
            # --- PHASE 1: Scrape the list-view page ---
            print(f"Fetching page {index}...")
            self.fetch(f"{base_url}&page={index}", page_type='list-view')

            print(
                f"Page {index} has fetched\nExtracting data from Page {index}...")
            # Extract basic info (id, title, price, location, url) for all listings on this page
            list_view_df = self.extract()

            print(f"Page {index} has been extracted")

            # Check if we got any listings on this page
            if list_view_df.empty:
                # If we get an empty DataFrame, it means we've hit the last page
                print("Found an empty page. Assuming this is the last page. Stopping.")
                break

            print(
                f"Found {len(list_view_df)} listings on page {index}. Starting detailed scraping...")

            # Convert DataFrame rows to dictionaries for easier manipulation
            listings = list_view_df.to_dict("records")

            time.sleep(randint(3, 8))

            # --- PHASE 2: Scrape detail page for each listing ---
            print(
                f"Starting detailed scraping for {len(listings)} listings...")

            for listing in listings:
                url = listing.get('url')
                listing_id = listing.get('listing_id', None)
                if not url:
                    # Skip listings without valid URLs
                    continue

                # Number of attempts failed while scraping this listing
                attempts = 0
                max_retries = 3
                success = False

                # This loop ensures that we wait if we get a soft-block and retry after that
                while attempts < max_retries and not success:
                    # Log which listing we're currently scraping
                    print(
                        f"Extracting details for ID:{listing_id}")

                    # Perform deep scrape of the detail page
                    details = self.extract_listing_details(url)

                    if details:
                        print(
                            f"Successfully scraped ID:{listing_id}. Last updated: {details.get('last_updated')}")

                        # Merge Phase 1 data (summary) with Phase 2 data (details)
                        # Later keys (from 'details') override earlier keys (from 'listing')
                        # This is the standard approach for combining data from multiple sources
                        full_listing_data = {**listing, **details}

                        # Add the complete record to our collection
                        all_data.append(full_listing_data)

                        success = True

                        print("Waiting for a few seconds before next listing...")
                        time.sleep(randint(3, 8))
                    else:
                        # If we've failed to get details of the current listing print warnin message and wait
                        attempts += 1
                        print(
                            f"Listing ID:{listing_id} couldn't be scraped ({attempts}/3)")

                        if attempts < max_retries:
                            wait_time = 60 * attempts
                            print(
                                f"Soft Block detected? Cooling down for {wait_time} seconds before retrying...")
                            time.sleep(wait_time)

                        else:
                            print(
                                f"Giving up on listing {listing_id} after {max_retries} attempts.")

                            time.sleep(randint(3, 8))

            if all_data:
                try:
                    # Create a DataFrame to store in the csv file
                    df_batch = pd.DataFrame(all_data)

                    file_name = f"page{index}.csv"

                    df_batch.to_csv(file_name, index=False)

                    print(f"{len(df_batch)} lines appended to {file_name}")

                    batch_files.append(file_name)
                    # Reset 'all_data' to reduce ram usage
                    all_data = []
                except PermissionError:
                    # Try an alternative filename
                    print(
                        f"ERROR: {file_name} might be open on another program")
                    file_name = f"page{index}_alt.csv"
                    df_batch.to_csv(file_name, index=False)
                    print(f"Original file locked, saved to {file_name}")
                    batch_files.append(file_name)
                except Exception as e:
                    print(
                        f"An unexpected error occurred while writing to csv file: {e}")

            # Add a polite delay to avoid overwhelming the server.
            print("Waiting for a few seconds before next page...")
            time.sleep(randint(3, 8))

        # If there are any saved files read them, concatinate them and then return them to the caller
        if batch_files:
            df = pd.concat(map(pd.read_csv, batch_files), ignore_index=True)
            return df
        else:
            print("No data was collected")
            return pd.DataFrame()

    def close(self):
        """Close the browser and terminate the WebDriver session.

        Ensures all browser windows are closed and resources are released.
        This method is automatically called when exiting the context manager.
        """
        self.driver.quit()
