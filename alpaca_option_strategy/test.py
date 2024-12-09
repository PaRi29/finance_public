import os
import csv
import time
import requests
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz

# Setup logging
logging.basicConfig(
    filename="options_tracker.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class OptionsTracker:
    def __init__(self):
        self.base_url = "https://paper-api.alpaca.markets"
        self.options_url = f"{self.base_url}/v2/options/contracts"
        self.headers = self._load_api_credentials()
        self.option_data = {}

    def _load_api_credentials(self):
        """Load API credentials from .env file."""
        load_dotenv()
        api_key = os.getenv("ALPACA_KEY")
        api_secret = os.getenv("ALPACA_SECRET")
        if not api_key or not api_secret:
            logging.error("API credentials not found in .env file.")
            raise ValueError("API credentials not found in .env file.")
        return {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }

    def fetch_put_options(self, ticker):
        """Fetch all put options for the given ticker."""
        params = {
            "underlying_symbols": ticker,
            "type": "put",
            "expiration_date_gte": datetime.now().strftime("%Y-%m-%d"),
            "expiration_date_lte": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            "limit": 10000,
        }
        response = requests.get(self.options_url, headers=self.headers, params=params)
        if response.status_code != 200:
            logging.error(f"Failed to fetch options for {ticker}: {response.text}")
            raise Exception(f"Failed to fetch options for {ticker}: {response.text}")
        return response.json().get("option_contracts", [])

    def save_initial_data(self, stocks):
        """Fetch and save initial options data."""
        for ticker in stocks:
            logging.info(f"Fetching initial data for {ticker}...")
            options = self.fetch_put_options(ticker)
            for option in options:
                symbol = option["symbol"]
                close_price = option.get("close_price")
                if close_price is not None:
                    self.option_data[symbol] = {
                        "price": float(close_price),
                        "details": option,
                    }

    def calculate_and_save_differences(self, stocks):
        """Fetch new data, calculate differences, and log the results."""
        for ticker in stocks:
            logging.info(f"Fetching updated data for {ticker}...")
            options = self.fetch_put_options(ticker)
            growth_data = {}

            for option in options:
                symbol = option["symbol"]
                close_price = option.get("close_price")
                if close_price is None:
                    continue

                new_price = float(close_price)
                if symbol in self.option_data:
                    old_price = self.option_data[symbol]["price"]
                    growth = new_price - old_price
                    growth_data[symbol] = {
                        "growth": growth,
                        "old_price": old_price,
                        "new_price": new_price,
                        "details": option,
                    }

            # Log the data
            if growth_data:
                with open("options_growth_log.txt", "a") as file:
                    for symbol, data in growth_data.items():
                        option_details = data["details"]
                        file.write(
                            f"{datetime.now()}: {symbol} | Growth: {data['growth']} | "
                            f"Old Price: {data['old_price']} | New Price: {data['new_price']} | "
                            f"Name: {option_details.get('name')} | "
                            f"Tradable: {option_details.get('tradable')} | "
                            f"Expiration Date: {option_details.get('expiration_date')} | "
                            f"Strike Price: {option_details.get('strike_price')}\n"
                        )

def main():
    # Load the single stock from CSV
    stock = None
    with open("stock_to_buy.csv", "r") as file:
        reader = csv.DictReader(file)  # Use DictReader for column-based access
        for row in reader:
            stock = row["Stock"]  # Take the "Stock" column value
            break  # Exit after the first row

    if not stock:  # If no stock is found, log and exit
        logging.warning("No stock found in stock_to_buy.csv. Exiting.")
        return

    tracker = OptionsTracker()

    # Step 1: Fetch initial data
    tracker.save_initial_data([stock])  # Single stock passed as a list

    # Step 2: Sleep until 15:35 Italian time
    italian_tz = pytz.timezone("Europe/Rome")
    now = datetime.now(italian_tz)
    target_time = now.replace(hour=15, minute=35, second=0, microsecond=0)
    if now > target_time:
        target_time += timedelta(days=1)

    time_to_sleep = (target_time - now).total_seconds()
    logging.info(f"Sleeping until {target_time} ({time_to_sleep / 3600:.2f} hours)")
    time.sleep(time_to_sleep)

    # Step 3: Calculate and save differences
    tracker.calculate_and_save_differences([stock])  # Single stock passed as a list

if __name__ == "__main__":
    main()
