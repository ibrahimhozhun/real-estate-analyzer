"""Main entry point for the real estate data scraper application.

This module orchestrates the scraping process by initializing the scraper,
fetching the target URL, extracting data, and displaying results.
"""

import os

import pandas as pd
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

            # Check if data.csv file exists
            file_exists = os.path.isfile("data.csv")

            if file_exists:
                # Get the data from our previous scrapings
                df = pd.read_csv("data.csv")
                # Concatinate old data with new data and store them in data.csv file
                pd.concat([df, all_data], ignore_index=True).to_csv(
                    "data.csv", index=False)
            else:
                all_data.to_csv("data.csv", index=False)
        else:
            print("No data was scraped.")
        print("------------------------")


if __name__ == "__main__":
    main()
