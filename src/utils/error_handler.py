"""Centralized error handling module for web scraping operations.

This module provides utility functions for handling Selenium-related
exceptions with appropriate logging and user-friendly error messages.
"""

from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException


def handle_scraping_exception(e: Exception):
    """Handle common Selenium scraping exceptions with descriptive messages.
    
    Examines the exception type and prints an appropriate error message to
    help diagnose scraping failures. This centralized approach ensures
    consistent error handling across the application.

    Args:
        e (Exception): The exception object caught in a try-except block.
    
    Note:
        This function currently prints to stdout. In production, consider
        logging to a file or monitoring service instead.
    """
    # Check for specific Selenium exception types and provide targeted messages
    if isinstance(e, NoSuchElementException):
        print("ERROR: An element was not found. The CSS selector might be outdated or the page structure has changed.")
    elif isinstance(e, TimeoutException):
        print("ERROR: The page load timed out while waiting for an element.")
    elif isinstance(e, WebDriverException):
        print(
            f"ERROR: A WebDriver-related error occurred. This could be a browser crash or a lost session. Details: {e}")
    else:
        # Catch-all for any other unexpected exceptions
        print(f"ERROR: An unexpected error occurred: {type(e).__name__} - {e}")
