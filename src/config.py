"""Configuration module for loading environment variables.

This module loads application configuration from the .env file using
python-dotenv. All sensitive data and configurable parameters should
be defined in the .env file, not hardcoded in the source code.
"""

from dotenv import load_dotenv
from os import getenv

# Load environment variables from .env file in the project root
load_dotenv()

# The target URL for scraping real estate data
DATA_URL = getenv("DATA_URL")
