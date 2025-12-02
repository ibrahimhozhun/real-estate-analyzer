"""Main entry point for the real estate data scraper application.

This module orchestrates the scraping process by initializing the scraper,
fetching the target URL, extracting data, and displaying results.
"""

from .config import DATA_URL
from .scraper import Scraper


def main():
    """Execute the main scraping workflow.
    
    Initializes the scraper using a context manager for safe resource handling,
    navigates to the configured data source URL, extracts listing data, and
    prints the resulting DataFrame to stdout.
    """
    # Use context manager to ensure browser cleanup even if errors occur
    with Scraper() as scraper:
        # Navigate to the target URL defined in configuration
        scraper.fetch(DATA_URL)

        # Extract structured data from the page
        df = scraper.extract()

        # Display extracted data
        print(df)


if __name__ == "__main__":
    main()
