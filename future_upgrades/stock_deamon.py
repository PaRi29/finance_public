import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
from datetime import datetime, timedelta
import time
from future_week_extractor.future_week_extractor import DividendDataExtractor
import csv
import shutil
import os
from dotenv import load_dotenv
import os
load_dotenv()

#todo controllare tramite file intermedio lesistenza di interim e final, aumentare la tolleranza al 2%

class StockSearcher:
    def __init__(self) -> None:
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    def _get_stock_data(self, stock_symbol):
        url = f"https://finance.yahoo.com/quote/{stock_symbol}/"

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7,en-GB;q=0.6',
            'cache-control': 'max-age=0',
            'cookie': 'GUC=AQABCAFm0cNnA0IebARG&s=AQAAANll0iRa&g=ZtB-1Q; A1=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAHD0WYDZ-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAAp2gCGvmSB0GzU9iM4gybEg; A3=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAHD0WYDZ-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAAp2gCGvmSB0GzU9iM4gybEg; A1S=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAHD0WYDZ-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAAp2gCGvmSB0GzU9iM4gybEg; PRF=t%3DTSLA%252BCHMI%252BCOF%252BKC%253DF%252BPRG%252BAHH%252BTDW%252BBCSF%252BE%252BAAPL%252BNVDA%252BRWT%252BTNSGF%252BLOGI%252BGHSI',

            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Brave";v="128"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        pre_market_price_tag = soup.find('fin-streamer', {
            'data-symbol': stock_symbol,
            'data-field': 'preMarketPrice'
        })
        if pre_market_price_tag:
            pre_market_price = pre_market_price_tag.get('data-value')
            return pre_market_price
        else:
            return None


    def find_highest_dividend_stocks(self, start_date, end_date, output_file="stock_to_buy.csv"):
        try:
            df = pd.read_csv("stock_to_buy.csv")
            print("CSV file read successfully")
            freq_map = {'semi-annual': 2, 'annual': 1,
                        'quarterly': 4, 'monthly': 12}
            df['Frequency_Number'] = df['Frequency'].map(
                lambda x: freq_map.get(str(x).lower(), 1) if pd.notna(x) else 100)


            # Funzione per la conversione del rendimento
            def convert_yield(yield_value):
                if pd.isna(yield_value) or yield_value == '-' or yield_value == '':
                    return 0.0  # Gestione di valori non validi come '-'
                try:
                    return float(str(yield_value).rstrip('%'))
                except ValueError:
                    return 0.0  # In caso di altri errori di conversione

            # Conversione del rendimento in float
            df['Yield'] = df['Yield'].apply(convert_yield)

            # Calcolo del rendimento aggiustato
            df['Adjusted_Yield'] = df['Yield'] / df['Frequency_Number']

            # Conversione della colonna 'Ex-Dividend Date' in datetime
            df['Ex-Dividend Date'] = pd.to_datetime(
                df['Ex-Dividend Date'], format="%b %d, %Y")
            print("Ex-Dividend Date conversion successful")

            # Iterazione tra le date e selezione dei migliori titoli
            results = []
            for current_date in pd.date_range(start=start_date, end=end_date):
                df_filtered_by_date = df[df['Ex-Dividend Date']== current_date]

                print(
                    f"Processing date: {current_date}, matching rows: {df_filtered_by_date.shape[0]}")

                if not df_filtered_by_date.empty:
                    top_stocks = df_filtered_by_date.nlargest(
                        40, 'Adjusted_Yield')

                    result = [
                        (current_date.strftime('%b %d, %Y'),
                         row['Ticker'], row['Adjusted_Yield']/100, row["Dividend"])
                        for _, row in top_stocks.iterrows()
                        if row['Adjusted_Yield'] > 3  # Controllo che l'Adjusted Yield sia sopra al 3%
                    ]
                    results.extend(result)
                    
            # Creazione di un DataFrame dai risultati
            results_df = pd.DataFrame(
                results, columns=['Date', 'Ticker', 'Adjusted_Yield', 'Dividend'])
            print(f"Results dataframe shape: {results_df.shape}")

            results_df.to_csv(output_file, index=False)
            print(f"Results saved to {output_file}")

            return results

        except Exception as e:
            print(
                f"Errore durante la ricerca degli stock con il yield da dividendo più alto: {e}")
            return []

    def find_best_stock(self, file_path="stock_to_buy.csv"):
        best_stocks = {}

        with open(file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                date = datetime.strptime(row['Date'], "%b %d, %Y").date()
                ticker = row['Ticker']
                adjusted_yield = float(row['Adjusted_Yield'])
                dividend = float(row['Dividend'])

                if date not in best_stocks:
                    best_stocks[date] = []
                best_stocks[date].append((ticker, adjusted_yield, dividend))

        final_best_stocks = {}

        for date, stocks in best_stocks.items():
            first_stock, first_yield, first_price_yeld = stocks[0]

            for stock, yield_value, yeld_price in stocks:
                price = self._get_stock_data(stock)
                print(stock, yield_value, yeld_price)
                if price is not None:
                    final_best_stocks[date] = (
                        stock, price, yeld_price, True)  
                    break
            if date not in final_best_stocks:
                final_best_stocks[date] = (
                    first_stock, None, first_price_yeld, False)
        output_file_path = "stock_to_buy.csv"

        with open(output_file_path, mode='w', newline='') as file:
            fieldnames = ['Date', 'Stock', 'Price', 'Yield Price', 'Has Pre']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for date, data in final_best_stocks.items():
                writer.writerow({
                    'Date': date.strftime("%b %d, %Y"),
                    'Stock': data[0],
                    'Price': data[1],
                    'Yield Price': data[2],
                    'Has Pre': data[3]
                })
        folders = ['finance_public/alpaca_dividend_strategy',
                   'finance_public/alpaca_short_strategy']
        for folder in folders:
            shutil.copy(output_file_path, os.path.join(
                folder, 'stock_to_buy.csv'))
        self.telegram_bot_sendtext(f"Best stocks saved to {output_file_path}")

    def find_next_week_date(self):
        today = datetime.today()
        current_monday = None
        current_friday = None
        if today.weekday() in [5, 6]:  # Sabato o Domenica
            return None, None  # Non fare nulla
        elif today.weekday() == 4:  # Venerdì
            # Calcoliamo il lunedì e venerdì della settimana prossima
            next_monday = today + timedelta(days=3)  # Lunedì prossimo
            next_friday = next_monday + timedelta(days=4)  # Venerdì prossimo
            return next_monday.strftime('%Y-%m-%d'), next_friday.strftime('%Y-%m-%d')
        else:  # Da lunedì a giovedì
            # Calcoliamo il lunedì e venerdì della settimana corrente
            current_monday = today - timedelta(days=today.weekday())  # Lunedì corrente
            current_friday = current_monday + timedelta(days=4)  # Venerdì corrente

        return current_monday.strftime('%Y-%m-%d'), current_friday.strftime('%Y-%m-%d')


    def telegram_bot_sendtext(self, messages):
        send_text = "https://api.telegram.org/bot"+self.TELEGRAM_BOT_TOKEN + \
            "/sendMessage?chat_id="+self.TELEGRAM_CHAT_ID + \
            "&text={}".format(str(messages))
        requests.get(send_text)


if __name__ == "__main__":

    searcher = StockSearcher()
    start_date, end_date = searcher.find_next_week_date()

    if start_date is None or end_date is None:  # Check for None values
        print("Today is Saturday or Sunday. Skipping stock search.")
        searcher.telegram_bot_sendtext(
            "Today is Saturday or Sunday. Skipping stock search.")

    else:
        searcher.telegram_bot_sendtext("ricercando nuovi stock")
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        print(start_date, end_date)
        extractor = DividendDataExtractor(start_date, end_date)
        extractor.extract_data()  # Save in stock_to_buy.csv

        searcher.find_highest_dividend_stocks(start_date, end_date)
        searcher.find_best_stock()
