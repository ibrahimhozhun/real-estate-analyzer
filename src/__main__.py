"""Main entry point for the real estate data scraper application.

This module orchestrates the scraping process by initializing the scraper,
fetching the target URL, extracting data, and displaying results.
"""

from .config import DATA_URL
from .scraper import Scraper


def main():
    """Execute the main scraping workflow.

    Initializes the scraper using a context manager for safe resource handling,
    navigates to the configured data source URL, scrapes a defined number of
    pages, and prints a summary of the resulting DataFrame to stdout.
    """
    # Use context manager to ensure browser cleanup even if errors occur
    with Scraper() as scraper:
        # Scrape the first 3 pages of listings for a development/test run
        all_data = scraper.scrape_multiple_pages(
            base_url=DATA_URL,
            start=1,
            stop=4  # Scrapes pages 1, 2, 3
        )

        print("\n--- Scraping Summary ---")
        print(f"Total listings scraped: {len(all_data)}")

        # Show a sample of the data if any was collected
        if not all_data.empty:
            print("Sample of collected data:")
            print(all_data.head())
        else:
            print("No data was scraped.")
        print("------------------------")


if __name__ == "__main__":
    main()
