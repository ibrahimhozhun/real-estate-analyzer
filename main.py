from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from os import getenv, path

# Find the absolute path for .env file
env_path = path.join(path.dirname(__file__), ".env")
# Load env variables from .env file
load_dotenv(dotenv_path=env_path)
# Get real estate website's url from env variables
DATA_URL = getenv("DATA_URL")

# Be sure to install required web driver for Selenium
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Load the website
driver.get(DATA_URL)

# Initialize prices list
prices = []

try:
    # Find elements that include prices
    price_elements = driver.find_elements(
        By.CSS_SELECTOR, "span.list-view-price")

    # Save prices to prices list
    for price in price_elements:
        prices.append(price.text)

except Exception as e:
    print(f"Bir hata oluştu: {e}")

finally:
    # Close the browser
    driver.quit()

# Print prices to confirm that we successfully got what we wanted
for price in prices:
    print(price)
