"""Web scraper module for extracting real estate listing data.

This module provides a Scraper class that uses Selenium to automate
browser interactions and extract structured data from real estate websites.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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

    def extract(self):
        """Extract structured data from real estate listings on the current page.

        Scrapes price and date information from listing elements and structures
        them into a pandas DataFrame for further analysis.

        Returns:
            pd.DataFrame: A DataFrame containing 'price' and 'date' columns.
                Returns an empty list if extraction fails.

        Note:
            Price text has the last 3 characters removed (assumes "TL" suffix).
            If an error occurs during extraction, it's handled by the
            error_handler module and an empty list is returned.
        """
        try:
            # Initialize list to collect listing data (converted to DataFrame later )
            data = []
            # Locate all elements that contain listings
            listings = self.driver.find_elements(
                By.CSS_SELECTOR, "div.list-view-content")

            for listing in listings:
                # Extract price text and strip currency suffix to enable numerical conversion
                price = listing.find_element(
                    By.CSS_SELECTOR, "span.list-view-price").text[:-3]
                # Extract listing publication date
                date = listing.find_element(
                    By.CSS_SELECTOR, "span.list-view-date").text

                # Add extracted fields to DataFrame
                data.append({
                    "price": price,
                    "date": date
                })

            # Convert collected data to DataFrame for analysis
            return pd.DataFrame(data)

        except Exception as e:
            # Delegate error handling to centralized error handler
            handle_scraping_exception(e)
            # Return empty DataFrame for consistency
            return pd.DataFrame()

    def close(self):
        """Close the browser and terminate the WebDriver session.

        Ensures all browser windows are closed and resources are released.
        This method is automatically called when exiting the context manager.
        """
        self.driver.quit()
