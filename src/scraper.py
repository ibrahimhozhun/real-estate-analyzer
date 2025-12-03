"""Web scraper module for extracting real estate listing data.

This module provides a Scraper class that uses Selenium to automate
browser interactions and extract structured data from real estate websites.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from .utils.error_handler import handle_scraping_exception
import pandas as pd


class Scraper:
    """A web scraper for extracting real estate data using Selenium.

    This class manages a Chrome WebDriver instance and provides methods to
    navigate to URLs and extract structured data from real estate listings.
    Implements context manager protocol for safe resource management.

    Attributes:
        driver (webdriver.Chrome): The Selenium WebDriver instance used for
            browser automation.

    Example:
        >>> with Scraper() as scraper:
        ...     scraper.fetch("https://example.com/listings")
        ...     data = scraper.extract()
    """

    def __init__(self):
        """Initialize the Scraper with a Chrome WebDriver instance.

        Automatically downloads and installs the appropriate ChromeDriver
        version using webdriver_manager, eliminating manual driver management.
        """
        # Initialize Chrome WebDriver with automatic driver management
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()))

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

    def fetch(self, url: str):
        """Navigate the browser to the specified URL.

        Args:
            url (str): The target URL to load in the browser.

        Note:
            This method waits for the page to load before returning.
        """
        self.driver.get(url)

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
        """Extract structured data from real estate listings on the list view page.

        Scrapes key features from each listing and structures them into a pandas
        DataFrame. Handles missing values gracefully by assigning None.

        Returns:
            pd.DataFrame: A DataFrame containing listing details. Columns include
                'title', 'price', 'date', 'location', 'room_count',
                'gross_square_meters', 'building_age', 'floor_type',
                and 'property_type'. Returns an empty DataFrame if the
                main extraction process fails.
        """
        try:
            # Initialize list to collect data from each listing (converted to DataFrame later )
            data = []
            # Locate all elements that contain listings
            listings = self.driver.find_elements(
                By.CSS_SELECTOR, "div.list-view-content")

            for listing in listings:
                # Use the helper method to safely extract raw text for each field
                listing_data = {
                    "title": self._safe_find_text(listing, "header.list-view-header > h3"),
                    "price": self._safe_find_text(listing, "span.list-view-price"),
                    "date": self._safe_find_text(listing, "span.list-view-date"),
                    "location": self._safe_find_text(listing, "span.list-view-location"),
                    "room_count": self._safe_find_text(listing, "span.celly.houseRoomCount"),
                    "gross_square_meters": self._safe_find_text(listing, "span.celly.squareMeter"),
                    "building_age": self._safe_find_text(listing, "span.celly.buildingAge"),
                    "floor_type": self._safe_find_text(listing, "span.celly.floortype"),
                    "property_type": self._safe_find_text(listing, "span.left")
                }

                data.append(listing_data)

            # Convert collected data to DataFrame for analysis
            return pd.DataFrame(data)

        except Exception as e:
            # Delegate error handling to centralized error handler
            handle_scraping_exception(e)
            # Return empty DataFrame for consistency
            return pd.DataFrame()

    def scrape_multiple_pages(self, base_url: str, start: int = 1, stop: int = 5):
        """
        Orchestrates the scraping of multiple listing pages.

        Navigates through paginated results, calling fetch() and extract()
        for each page, and aggregates the results into a single DataFrame.

        Args:
            base_url (str): The base URL for the listings. It is assumed to
                            contain query parameters, so new params are
                            appended with '&'.
            start (int): The starting page number.
            stop (int): The page number to stop before (e.g., stop=5 scrapes 1-4).

        Returns:
            pd.DataFrame: A single DataFrame containing data from all scraped pages.
        """
        all_dataframes = []

        for index in range(start, stop):
            print(f"Fetching page {index}...")
            self.fetch(f"{base_url}&page={index}")

            print(
                f"Page {index} has fetched\nExtracting data from Page {index}...")
            df = self.extract()

            print(f"Page {index} has been extracted")

            if not df.empty:
                all_dataframes.append(df)
            else:
                # If we get an empty DataFrame, it means we've hit the last page
                print("Found an empty page. Assuming this is the last page. Stopping.")
                break

            # Add a polite delay to avoid overwhelming the server.
            print("Waiting for 2 seconds before next page...")
            time.sleep(2)

        # Only concatenate if we have collected data.
        if all_dataframes:
            return pd.concat(all_dataframes, ignore_index=True)
        else:
            print("No data was collected.")
            return pd.DataFrame()

    def close(self):
        """Close the browser and terminate the WebDriver session.

        Ensures all browser windows are closed and resources are released.
        This method is automatically called when exiting the context manager.
        """
        self.driver.quit()
