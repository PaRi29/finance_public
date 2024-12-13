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
        """Fetch new data, calculate differences, and log the top 5 results by growth percentage."""
        for ticker in stocks:
            logging.info(f"Fetching updated data for {ticker}...")
            options = self.fetch_put_options(ticker)
            growth_data = []  # Changed to list for easier sorting

            for option in options:
                symbol = option["symbol"]
                close_price = option.get("close_price")
                if close_price is None:
                    continue

                new_price = float(close_price)
                if symbol in self.option_data:
                    old_price = self.option_data[symbol]["price"]
                    if old_price == 0:  # Avoid division by zero
                        continue
                    growth = new_price - old_price
                    growth_percentage = (growth / old_price) * 100  # Calculate percentage
                    growth_data.append({
                        "symbol": symbol,
                        "growth": growth,
                        "growth_percentage": growth_percentage,
                        "old_price": old_price,
                        "new_price": new_price,
                        "details": option,
                    })

            # Sort by growth percentage and get top 5
            growth_data.sort(key=lambda x: x['growth_percentage'], reverse=True)
            top_5_growth = growth_data[:5]

            # Log only the top 5
            if top_5_growth:
                with open("options_growth_log.txt", "a") as file:
                    file.write(f"\n=== Top 5 Options by Growth Percentage for {ticker} at {datetime.now()} ===\n")
                    for data in top_5_growth:
                        option_details = data["details"]
                        file.write(
                            f"{data['symbol']} | Growth %: {data['growth_percentage']:.2f}% | "
                            f"Growth: ${data['growth']:.2f} | "
                            f"Old Price: ${data['old_price']:.2f} | "
                            f"New Price: ${data['new_price']:.2f} | "
                            f"Name: {option_details.get('name')} | "
                            f"Tradable: {option_details.get('tradable')} | "
                            f"Expiration Date: {option_details.get('expiration_date')} | "
                            f"Strike Price: {option_details.get('strike_price')}\n"
                        )
                    file.write("=" * 80 + "\n")

def wait_until_evening():
    """Wait until 20:00 Italian time."""
    it_tz = pytz.timezone('Europe/Rome')
    current_time = datetime.now(it_tz)
    target_time = current_time.replace(hour=20, minute=30, second=0, microsecond=0)
    
    # If target time has passed today, wait for tomorrow's target time
    if current_time > target_time:
        target_time = target_time + timedelta(days=1)

    # Calculate wait time in seconds
    wait_seconds = (target_time - current_time).total_seconds()
    logging.info(f"Waiting {wait_seconds} seconds until {target_time.strftime('%H:%M:%S')}")
    time.sleep(wait_seconds)

def main():
    # Load the single stock from CSV
    stock = None
    with open("stock_to_buy.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            stock = row["Stock"]
            break

    if not stock:
        logging.warning("No stock found in stock_to_buy.csv. Exiting.")
        return

    tracker = OptionsTracker()

    # Wait until 20:00 Italian time before getting initial data
    wait_until_evening()

    # Get initial data
    logging.info(f"Fetching initial data for {stock}...")
    tracker.save_initial_data([stock])

    # Get current time in Italy
    it_tz = pytz.timezone('Europe/Rome')
    current_time = datetime.now(it_tz)

    if current_time.weekday() != 4:  # If today is not Friday
        target_time = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
    else:  # If today is Friday, set target time to 15:30 of next Monday
        target_time = current_time + timedelta(days=3)
        target_time = target_time.replace(hour=15, minute=30, second=0, microsecond=0)
        print(target_time)
    
    # If target time has passed today, wait for tomorrow's target time
    if current_time > target_time:
        target_time = target_time + timedelta(days=1)

    # Calculate wait time in seconds
    wait_seconds = (target_time - current_time).total_seconds()
    logging.info(f"Waiting {wait_seconds} seconds until {target_time.strftime('%H:%M:%S')}")
    time.sleep(wait_seconds)

    # Get final data and calculate differences once
    logging.info(f"Calculating differences for {stock}...")
    tracker.calculate_and_save_differences([stock])
    logging.info("Completed options tracking. Exiting.")

if __name__ == "__main__":
    main()
