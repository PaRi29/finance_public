

import datetime
import requests
import csv
from pathlib import Path
import time
import pandas as pd
import pytz
from dotenv import load_dotenv
import os
import yfinance as yf
from bs4 import BeautifulSoup
import re
import logging
import alpaca_trade_api as tradeapi
import asyncio
import websockets
import json
import base64
from google.protobuf import descriptor_pool, message_factory, descriptor_pb2





class DividendTradingSimulator:
    def __init__(self, initial_budget=1000, simulation_days=30, commission=1.0, short_borrow_rate=0.003):
        self.ALPACA_API=tradeapi.REST(ALPACA_API_KEY, API_SECRET, ALPACA_ENDPOINT, api_version='v2')  
        self.budget = float(self.ALPACA_API.get_account().cash)- 25000
        print(self.budget)
        self.dividend_balance = 0
        self.simulation_days = simulation_days
        self.current_simulation_day = 0
        self.transactions = []
        self.csv_file = Path("dividend_trading_results.csv")
        self.italy_tz = pytz.timezone('Europe/Rome')
        self.stock_to_buy = None
        self.has_pre = True
        self.dividend_per_action = 0
        self.tomorrow_date_number = 0
        self.stock_data = pd.read_csv("stock_to_buy.csv")
        self.commission = commission
        self.short_borrow_rate = short_borrow_rate
        self.short_commission = 1.0
        self.short_close_commission = 1.0
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
        self.tax_rate = 0.27  # 27% tax rate
        self.close_price=0
        self.open_price=0
        self.current_price=None
        self.is_position_closed=False
        self.is_short_open=False
        self.stop_simulation = False  # Flag to stop the simulation
        self.pricing_data_message = self.create_pricing_data_message()

    def run_simulation(self):
        self.initialize_csv()
        while self.current_simulation_day < self.simulation_days:
            self.is_position_closed=False
            self.is_short_open=False

            logging.info(f"Giorno {self.current_simulation_day + 1}")
            self.telegram_bot_sendtext(
                f"Giorno {self.current_simulation_day + 1}")

            start_time = self.get_next_time(hour=20, minute=0)
            wait_time = (start_time - datetime.datetime.now(self.italy_tz)).total_seconds()

            if wait_time > 0:
                time.sleep(wait_time)
                time.sleep(3)

            self.stock_data = pd.read_csv("stock_to_buy.csv")
            self.tomorrow_date_number = (datetime.datetime.now(
                self.italy_tz) + datetime.timedelta(days=1)).strftime('%b %d, %Y')
            
            stock_info = self.get_stock_info_for_tomorrow()
            if stock_info is None and datetime.datetime.now(self.italy_tz).weekday() != 6:

                if datetime.datetime.now(self.italy_tz).weekday() <4:
                    logging.info(
                        "Nessuno stock da comprare domani. Aspettando il giorno successivo...")
                    self.telegram_bot_sendtext(
                        "Nessuno stock da comprare domani. Aspettando il giorno successivo...")
                    time.sleep(23 * 3600)  # Dorme per un giorno
                    self.current_simulation_day += 1
                    continue

                elif datetime.datetime.now(self.italy_tz).weekday() == 4:  # Venerdì
                    logging.info(
                        "Nessuno stock da comprare domani e oggi è venerdì. Comprando l'azione di lunedì...")
                    self.telegram_bot_sendtext(
                        "Nessuno stock da comprare domani e oggi è venerdì. Comprando l'azione di lunedì...")
                    self.tomorrow_date_number = (datetime.datetime.now(
                        self.italy_tz) + datetime.timedelta(days=3)).strftime('%b %d, %Y')
                    stock_info = self.get_stock_info_for_tomorrow()

                    if stock_info is None:
                        logging.info(
                            "Nessuno stock disponibile per lunedì. Aspettando il giorno successivo...")
                        self.telegram_bot_sendtext(
                            "Nessuno stock disponibile per lunedì. Aspettando il giorno successivo...")
                        time.sleep(23 * 3600 * 3)  # Dorme per un giorno
                        self.current_simulation_day += 3
                        continue

                elif datetime.datetime.now(self.italy_tz).weekday() == 5:
                    logging.info(
                        "non dovrei essere qua, oggi è sabato, torno a dormire fino e lunedì...")
                    self.telegram_bot_sendtext(
                        "non dovrei essere qua, oggi è sabato, torno a dormire fino e lunedì...")
                    monday_morning = self.get_next_sell_time() + datetime.timedelta(days=1)
                    wait_time = (
                        monday_morning - datetime.datetime.now(self.italy_tz)).total_seconds()
                    if wait_time > 0:
                        logging.info(wait_time)
                        time.sleep(wait_time)

            elif stock_info is None and datetime.datetime.now(self.italy_tz).weekday() == 6:
                    logging.info(
                        "non dovrei essere qua, oggi è domenica, torno a dormire fino a lunedì...")
                    self.telegram_bot_sendtext(
                        "non dovrei essere qua, oggi è domenica, torno a dormire fino a lunedì...")
                    monday_morning = self.get_next_sell_time() 
                    wait_time = (
                        monday_morning - datetime.datetime.now(self.italy_tz)).total_seconds()
                    if wait_time > 0:
                        logging.info(wait_time)
                        time.sleep(wait_time)

            self.stock_to_buy, price_, self.dividend_per_action, self.has_pre = stock_info
            
            logging.info("Stock: %s, Price: %s, Dividend: %s, Has Pre: %s", 
                          self.stock_to_buy, price_,
                          self.dividend_per_action, self.has_pre)

            buy_time = self.get_next_time(hour=21, minute=58)
            wait_time = (
                buy_time - datetime.datetime.now(self.italy_tz)).total_seconds()
            logging.info(wait_time)

            if wait_time > 0:
                logging.info(f"In attesa fino alle {buy_time} per l'acquisto...")
                time.sleep(wait_time)


            self.open_price = float(self.get_stock_price_intraday(self.stock_to_buy))
            print(self.open_price) 
            limit_price= self.open_price*1.003
            rounded_limit_price = round(limit_price, 2)
            print(f"Budget: {self.budget}, Open Price: {self.open_price}")

            shares_bought = abs(self.budget // (self.open_price))
            cost = shares_bought * self.open_price + self.commission  

            print(shares_bought)
            status=self.alpaca_buy_intraday(self.stock_to_buy,shares_bought)

            self.current_simulation_day += 1
            limit_price= self.open_price*0.98
            rounded_limit_price = round(limit_price, 2)

            if status:
                logging.info(
                f"Comprando {shares_bought} azioni di {self.stock_to_buy} a ${self.open_price:.2f} alle {buy_time}")
                self.telegram_bot_sendtext(
                f"Comprando {shares_bought} azioni di {self.stock_to_buy} a ${self.open_price:.2f} alle {buy_time}")

            else:
                self.telegram_bot_sendtext(f"tenteativo di compera di {shares_bought} azioni di {self.stock_to_buy} non riuscito, attendo il giorno successivo")
                time.sleep(60*60*10)
                continue
            

            #wait_time = (self.get_next_time(hour=10, minute=0) - datetime.datetime.now(self.italy_tz)).total_seconds()# controllo del venerdì qua
            if datetime.datetime.now(self.italy_tz).weekday() == 4:  # Venerdì
                monday_morning = self.get_next_time(hour=10, minute=0) + datetime.timedelta(days=2)
                wait_time = (monday_morning - datetime.datetime.now(self.italy_tz)).total_seconds()
                if wait_time > 0:
                    logging.info(f"In attesa fino alle {monday_morning} per chiudere la posizione e vendere allo scoperto...")
                    logging.info(wait_time)
                    time.sleep(wait_time)

                    no_hope_time = self.get_next_time(hour=10, minute=59)
                    while datetime.datetime.now(self.italy_tz) < no_hope_time:
                        if self.is_easy_to_short(self.stock_to_buy):
                            break
                        time.sleep(0.5)

                    try:
                        self.open_price = float(self.get_stock_price_pre(self.stock_to_buy))
                    except:
                        try:
                            self.open_price= float(self.get_stock_price_post((self.stock_to_buy)))
                        except:
                            self.open_price= float(self.get_stock_price_intraday((self.stock_to_buy)))

                    shares_bought = self.budget // (self.open_price)
                    limit_price= self.open_price*0.98
                    rounded_limit_price = round(limit_price, 2)

                    self.is_position_closed = self.close_buy_position_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)
                    time.sleep(10)
                    if self.is_position_closed:
                        self.is_short_open = self.short_sell_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)
                    else:
                        self.is_short_open = False
            else:  # Altri giorni della settimana
                next_morning = self.get_next_time(hour=10, minute=0)
                wait_time = (next_morning - datetime.datetime.now(self.italy_tz)).total_seconds()
                if wait_time > 0:
                
                    logging.info(f"In attesa fino alle {next_morning} per chiudere la posizione e vendere allo scoperto...")
                    logging.info(wait_time)
                    time.sleep(wait_time)

                    no_hope_time = self.get_next_time(hour=10, minute=59)
                    while datetime.datetime.now(self.italy_tz) < no_hope_time:
                        if self.is_easy_to_short(self.stock_to_buy):
                            break
                        time.sleep(0.5)

                    try:
                        self.open_price = float(self.get_stock_price_pre(self.stock_to_buy))
                    except:
                        try:
                            self.open_price= float(self.get_stock_price_post((self.stock_to_buy)))
                        except:
                            self.open_price= float(self.get_stock_price_intraday((self.stock_to_buy)))

                    shares_bought = self.budget // (self.open_price)
                    limit_price= self.open_price*0.98
                    rounded_limit_price = round(limit_price, 2)


                    self.is_position_closed = self.close_buy_position_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)
                    time.sleep(10)
                    if self.is_position_closed:
                        self.is_short_open = self.short_sell_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)
                    else:
                        self.is_short_open= False

            time.sleep(60)
            if not self.is_position_closed:
                first_afternoon= self.get_next_time(hour=15, minute=30)
                wait_time = (first_afternoon - datetime.datetime.now(self.italy_tz)).total_seconds()
                if wait_time > 0:
                    logging.info(f"la posizione non era ancora chiusa, aspettiamo le 15:30 e speriamo")
                    logging.info(wait_time)
                    time.sleep(wait_time)
                    time.sleep(1)
                    self.ALPACA_API.cancel_all_orders()
                    time.sleep(5)

                    self.open_price = float(self.get_stock_price_intraday(self.stock_to_buy))
                    shares_bought = self.budget // (self.open_price)
                    limit_price= self.open_price*0.98
                    rounded_limit_price = round(limit_price, 2)

                    self.is_position_closed = self.close_buy_position_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)
                    time.sleep(10)
                    self.is_short_open = self.short_sell_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)
            
            elif self.is_position_closed and not self.is_short_open:
                first_afternoon= self.get_next_time(hour=15, minute=30)
                wait_time = (first_afternoon - datetime.datetime.now(self.italy_tz)).total_seconds()
                if wait_time > 0:
                    logging.info(f"la posizione era chiusa, ma lo short non era aperto, aspettiamo le 15:30 e speriamo")
                    logging.info(wait_time)
                    time.sleep(wait_time)
                    time.sleep(1)
                    self.ALPACA_API.cancel_all_orders()
                    time.sleep(5)

                    self.open_price = float(self.get_stock_price_intraday(self.stock_to_buy))
                    shares_bought = self.budget // (self.open_price)
                    limit_price= self.open_price*0.98
                    rounded_limit_price = round(limit_price, 2)
                    
                    self.is_short_open = self.short_sell_pre_hours(self.stock_to_buy, shares_bought, rounded_limit_price)

            sell_time = self.get_next_time(hour=15, minute=32)
            wait_time = (
                sell_time - datetime.datetime.now(self.italy_tz)).total_seconds()

            asyncio.run(self.run_short_selling(self.stock_to_buy,self.open_price,shares_bought))
            logging.info(f"comprando {shares_bought} azioni di {self.stock_to_buy} a ${self.close_price:.2f} alle {sell_time}")
            self.telegram_bot_sendtext(f"comprando {shares_bought} azioni di {self.stock_to_buy} a ${self.close_price:.2f} alle {sell_time}")

            time.sleep(600)
            gross_dividend = shares_bought * self.dividend_per_action
            logging.info(gross_dividend)
            net_dividend = gross_dividend * \
                (1 - self.tax_rate)  # Apply tax to dividends
            self.dividend_balance += net_dividend

            prev_budget=self.budget
            self.budget = float(self.ALPACA_API.get_account().cash)- 25000
            profit_loss= self.budget-prev_budget

            transaction = {
                "day": self.current_simulation_day,
                "stock": self.stock_to_buy,
                "shares": shares_bought,
                "open_price": self.open_price,
                "close_price": self.close_price,
                "profit_loss": profit_loss,
                "dividend": net_dividend,
                "budget": self.budget,
                "dividend_balance": self.dividend_balance
            }

            self.transactions.append(transaction)
            self.save_transaction_to_csv(transaction)

            logging.info(f"Profitto/Perdita: ${profit_loss:.2f}")
            logging.info(f"Dividendo netto: ${net_dividend:.2f}")
            logging.info(f"Nuovo budget: ${self.budget:.2f}")
            logging.info(f"Bilancio dividendi: ${self.dividend_balance:.2f}")
            logging.info("---")

            day_summary = (
                "\n--- Riepilogo giornaliero ---\n"
                f"Giorno: {self.current_simulation_day}\n"
                "==================================="
            )
            portfolio_summary = (
                f"stock:  {self.stock_to_buy}\n"
                f"Profitto/Perdita: ${profit_loss:.2f}\n"
                f"Totale Portafoglio: ${self.budget:.2f}\n"
                "==================================="
            )
            dividend_summary = (
                f"Profitto Dividendo: ${net_dividend:.2f}\n"
                f"Bilancio dividendi: ${self.dividend_balance:.2f}\n"
                "==================================="
            )
            self.telegram_bot_sendtext("===================================")
            self.telegram_bot_sendtext(day_summary)
            self.telegram_bot_sendtext(portfolio_summary)
            self.telegram_bot_sendtext(dividend_summary)
            self.telegram_bot_sendtext("===================================")

        total_profit_loss = self.budget - 26000  # 1000 è il budget iniziale
        logging.info("\n--- Riepilogo finale ---")
        logging.info(f"Bilancio P/L: ${total_profit_loss:.2f}")
        logging.info(f"Bilancio dividendi: ${self.dividend_balance:.2f}")

        self.telegram_bot_sendtext("\n--- Riepilogo finale ---")
        self.telegram_bot_sendtext(f"Bilancio P/L: ${total_profit_loss:.2f}")
        self.telegram_bot_sendtext(
            f"Bilancio dividendi: ${self.dividend_balance:.2f}")

    def initialize_csv(self):
        headers = ["day", "stock", "shares", "buy_price", "sell_price", "profit_loss",
                   "dividend", "short_profit", "budget", "dividend_balance"]
        with open(self.csv_file, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()

    def save_transaction_to_csv(self, transaction):
        with open(self.csv_file, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=transaction.keys())
            writer.writerow(transaction)

    def get_stock_info_for_tomorrow(self):
        stock_info = self.stock_data[self.stock_data['Date']
                                     == self.tomorrow_date_number]
        if stock_info.empty:
            return None
        stock_info = stock_info.iloc[0]
        stock_name = stock_info['Stock']
        try:
            stock_name = re.search(r'\((.*?)\)', stock_name).group(1)
        except:
            pass
        return stock_name, stock_info['Price'], stock_info['Yield Price'], stock_info['Has Pre']

    def get_stock_price_intraday(self, symbol):
        url = f"https://finance.yahoo.com/quote/{symbol}/"

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7,en-GB;q=0.6',
            'cache-control': 'max-age=0',
            'cookie': 'GUC=AQABCAFnBjRnNEIebARG&s=AQAAAFQYrj8Z&g=ZwTq1w; A1=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAE0Bmc0Z-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAApqIdw8jfGQpaBGxN4l0MQs; A3=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAE0Bmc0Z-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAApqIdw8jfGQpaBGxN4l0MQs; A1S=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAE0Bmc0Z-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAApqIdw8jfGQpaBGxN4l0MQs; PRF=t%3DAAPL%252BTSLA%252BSQ%252BQS%252BSAVE%252BHON%252BQBTS%252BQUBT%252BARQQ%252BRGTI%252BIONQ%252BNNE%252BD%252BNWE%252BTSQ; A1=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAETJWdMZ-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAAgUGiq5KjXPmkEc267014tc; A1S=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAETJWdMZ-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAAgUGiq5KjXPmkEc267014tc; A3=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAETJWdMZ-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAAgUGiq5KjXPmkEc267014tc; EuConsent=CQGLJwAQGLJwAAOACKITBNFgAAAAAAAAACiQAAAAAAAA; GUC=AQABCAFnJRNnTEIebARG&s=AQAAAE3srCJw&g=ZyPGKg; GUCS=ASlPb4q1',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="130", "Brave";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print("Error fetching the page.")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        # Locate the stock price element based on its class and data-testid
        stock_price_element = soup.find("fin-streamer", {"class": "livePrice yf-1tejb6", "data-testid": "qsp-price"})

        if stock_price_element:
            return stock_price_element.text
        else:
            print("Could not find the stock price element.")
            return None

    def get_stock_price_pre(self, symbol):
        url = f"https://finance.yahoo.com/quote/{symbol}/"

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
            'data-symbol': symbol,
            'data-field': 'preMarketPrice'
        })
        if pre_market_price_tag:
            pre_market_price = pre_market_price_tag.get('data-value')
            return pre_market_price
        else:
            return None

    def get_stock_price_post(self, symbol):
        url = f"https://finance.yahoo.com/quote/{symbol}/"

        headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7,en-GB;q=0.6',
        'cache-control': 'max-age=0',
        'cookie': 'GUC=AQABCAFnBjRnNEIebARG&s=AQAAAFQYrj8Z&g=ZwTq1w; A1=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAE0Bmc0Z-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAApqIdw8jfGQpaBGxN4l0MQs; A3=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAE0Bmc0Z-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAApqIdw8jfGQpaBGxN4l0MQs; A1S=d=AQABBGE0d2MCEBTQP0_77ONRfiPRkQ9IyVcFEgABCAE0Bmc0Z-dVb2UBAiAAAAcIYTR3Yw9IyVc&S=AQAAApqIdw8jfGQpaBGxN4l0MQs; PRF=t%3DTSLA%252BFNLC%252BNVDA%252BGAIN%252BTWO%252BCABO%252BCHMI%252BCOF%252BKC%253DF%252BPRG%252BAHH%252BTDW%252BBCSF%252BE%252BAAPL',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Brave";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')

        post_market_price = soup.find('fin-streamer', {'data-field': 'postMarketPrice'})
        if post_market_price:
            return post_market_price['data-value']
        else:
            return None


    async def connect_to_yahoo(self, symbol):
        """Connect to Yahoo Finance WebSocket and update self.current_price with feed data."""
        BASE_URL = 'wss://streamer.finance.yahoo.com'
        
        while not self.stop_simulation:  # Loop to handle reconnections
            try:
                async with websockets.connect(BASE_URL) as websocket:
                    logging.info(f"Connected to Yahoo Finance WebSocket for {symbol}.")
                    subscribe_message = {"subscribe": [symbol]}
                    await websocket.send(json.dumps(subscribe_message))

                    while not self.stop_simulation:
                        message = await websocket.recv()
                        decoded_data = self.decode_protobuf_message(message)
                        if decoded_data and decoded_data.id == symbol:
                            self.current_price = decoded_data.price
                            logging.info(f"Current price for {symbol}: {self.current_price}")

            except websockets.exceptions.ConnectionClosed:
                logging.info("WebSocket connection closed. Reconnecting in 1 minute...")
                await asyncio.sleep(60)  # Wait 1 minute before trying to reconnect

            except Exception as e:
                logging.info(f"Error in WebSocket connection: {e}. Reconnecting in 1 minute...")
                await asyncio.sleep(60)  # Wait 1 minute before trying to reconnect

    async def simulate_short_selling(self, symbol, initial_price, shares_sold):
        """Simulate short selling monitoring stop loss, stop gain, or market close."""
        borrow_cost = shares_sold * initial_price * self.short_borrow_rate
        stop_gain = -0.5 * self.dividend_per_action / initial_price
        stop_loss = 0.01
        market_close_time = datetime.time(21, 50)

        while not self.stop_simulation:
            current_time = datetime.datetime.now(self.italy_tz).time()

            # Check market close condition
            if current_time >= market_close_time:
                logging.info(f"Market closed at {current_time}, ending simulation.")
                self.stop_simulation = True
                return self.calculate_short_profit(symbol, initial_price, shares_sold, borrow_cost)

            # Wait for current price to be updated
            if self.current_price is None:
                await asyncio.sleep(1)
                continue
            price_change = (self.current_price - initial_price) / initial_price

            # Check stop loss condition
            if price_change >= stop_loss:
                logging.info(f"Stop loss triggered at {self.current_price:.2f}")
                self.stop_simulation = True
                return self.calculate_short_profit(symbol, initial_price, shares_sold, borrow_cost)

            # Check stop gain condition
            if price_change <= stop_gain:
                logging.info(f"Stop gain triggered at {self.current_price:.2f}")
                self.stop_simulation = True
                return self.calculate_short_profit(symbol, initial_price, shares_sold, borrow_cost)

            await asyncio.sleep(1)  # Sleep for a short duration before checking again

    def calculate_short_profit(self, symbol, initial_price, shares_sold, borrow_cost):
        """Calcola il profitto finale della vendita allo scoperto."""
        self.close_price = self.current_price  # Usa il prezzo corrente per chiudere la posizione
        self.close_position(symbol)

        short_profit = (initial_price - self.close_price) * shares_sold - borrow_cost - self.short_commission - self.short_close_commission

        # Applica tasse sui profitti
        if short_profit > 0:
            short_profit *= (1 - self.tax_rate)
        logging.info(f"Profit from short selling {symbol}: {short_profit:.2f}")
        return short_profit
    

    def close_position(self, symbol):
        try:
            # Get the position for the specified symbol
            position = self.ALPACA_API.get_position(symbol)

            # Get the quantity as an integer
            qty = abs(int(position.qty))

            # Determine if the position is long (buy) or short (sell)
            if position.side == 'long':
                # Close the long position by selling the shares
                self.ALPACA_API.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                logging.info(f'Closed long position for {symbol}.')
            elif position.side == 'short':
                # Close the short position by buying the shares
                self.ALPACA_API.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='gtc'
                )
                logging.info(f'Closed short position for {symbol}.')
            else:
                logging.info(f'No open position for {symbol}.')
        except tradeapi.rest.APIError as e:
            logging.info(f'Error closing position for {symbol}: {e}')
        except Exception as e:
            logging.info(f'An unexpected error occurred: {e}')


    async def run_short_selling(self, symbol, initial_price, shares_sold):
            """Run the WebSocket and short selling simulation concurrently."""
            await asyncio.gather(
                self.connect_to_yahoo(symbol),  # Task to handle WebSocket data
                self.simulate_short_selling(symbol, initial_price, shares_sold)  # Task to handle simulation logic
            )

    def create_pricing_data_message(self):
        pool = descriptor_pool.Default()
        file_descriptor_proto = descriptor_pb2.FileDescriptorProto()

        file_descriptor_proto.name = "pricing.proto"
        file_descriptor_proto.package = "quotefeeder"

        message_type = file_descriptor_proto.message_type.add()
        message_type.name = "PricingData"

        fields = [
            ("id", 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ("price", 2, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
            ("time", 3, descriptor_pb2.FieldDescriptorProto.TYPE_SINT64),
            ("currency", 4, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ("exchange", 5, descriptor_pb2.FieldDescriptorProto.TYPE_STRING),
            ("quote_type", 6, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
            ("market_hours", 7, descriptor_pb2.FieldDescriptorProto.TYPE_INT32),
            ("change_percent", 8, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
            ("day_volume", 9, descriptor_pb2.FieldDescriptorProto.TYPE_SINT64),
            ("change", 12, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT),
            ("price_hint", 27, descriptor_pb2.FieldDescriptorProto.TYPE_SINT64),
        ]

        for name, number, field_type in fields:
            field = message_type.field.add()
            field.name = name
            field.number = number
            field.type = field_type
            field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL

        file_descriptor = pool.Add(file_descriptor_proto)
        factory = message_factory.MessageFactory(pool)
        return factory.GetPrototype(file_descriptor.message_types_by_name['PricingData'])

    def decode_protobuf_message(self, base64_message):
        try:
            decoded_bytes = base64.b64decode(base64_message)
            message = self.pricing_data_message()
            message.ParseFromString(decoded_bytes)
            return message
        except Exception as e:
            logging.info(f"Failed to decode Protobuf message: {e}")
            return None

    def get_next_time(self, hour, minute):
        now = datetime.datetime.now(self.italy_tz)
        next_time = now.replace(hour=hour, minute=minute,
                                second=0, microsecond=0)
        if next_time <= now:
            next_time += datetime.timedelta(days=1)
        return next_time

    def get_next_sell_time(self):
        if True: #self.has_pre == True:
            return self.get_next_time(hour=10, minute=0)
        #else:
            #return self.get_next_time(hour=15, minute=30)

    def sleep_until(self, target_time):
        now = datetime.datetime.now(self.italy_tz)
        wait_time = (target_time - now).total_seconds()
        if wait_time > 0:
            time.sleep(wait_time)

    def sleep_until_next_day(self):
        now = datetime.datetime.now(self.italy_tz)
        next_day = now + datetime.timedelta(days=1)
        next_day_start = next_day.replace(
            hour=0, minute=0, second=0, microsecond=0)
        self.sleep_until(next_day_start)

    def telegram_bot_sendtext(self, messages):
        send_text = "https://api.telegram.org/bot"+self.TELEGRAM_BOT_TOKEN + \
            "/sendMessage?chat_id="+self.TELEGRAM_CHAT_ID + \
            "&text={}".format(str(messages))
        requests.get(send_text)

    def is_easy_to_short(self, symbol):
        asset = self.ALPACA_API.get_asset(symbol)
        try:
            if asset.easy_to_borrow:
                return True
            else:
                return False
        except:
            return False

    def alpaca_buy_intraday(self, ticker, quantity):
        order = self.ALPACA_API.submit_order(
        symbol=ticker,
        qty=quantity,
        side='buy',          # Close position by selling
        type='market',         # Limit order type
        time_in_force='day',  # Day order for extended hours
        )  
        sell_order_id = order.id
        
        for _ in range(3600):  # Check every second for up to 60 seconds
            if self.is_order_filled(sell_order_id):
                logging.info("Buy position closed successfully.")
                return True
            time.sleep(1)
        logging.info("Failed to close buy position within the time limit.")
        return False


    def is_order_filled(self, order_id):
        order = self.ALPACA_API.get_order(order_id)
        return order.status == 'filled'

    def close_buy_position_pre_hours(self, symbol, qty, limit_price_sell):
        """
        Closes an open buy position in after-hours.

        Parameters:
        - symbol (str): The stock ticker symbol to close.
        - qty (int): The number of shares to sell.
        - limit_price_sell (float): The limit price to close the buy position.

        Returns:
        - (bool): True if the sell order is filled, False otherwise.
        """
        # Place the order to sell the buy position after hours
        sell_order = self.ALPACA_API.submit_order(
            symbol=symbol,
            qty=qty,
            side='sell',          # Close position by selling
            type='limit',         # Limit order type
            limit_price=limit_price_sell,
            time_in_force='day',  # Day order for extended hours
            extended_hours=True   # Allows after-hours trading
        )

        sell_order_id = sell_order.id
        
        # Wait and check if the sell order is filled
        for _ in range(3600):  # Check every second for up to 60 seconds
            if self.is_order_filled(sell_order_id):
                logging.info("Buy position closed successfully.")
                return True
            time.sleep(1)

        logging.info("Failed to close buy position within the time limit.")
        return False
    

    def short_sell_pre_hours(self, symbol, qty, limit_price_short):
        """
        Places a short sell order for a stock in after-hours.

        Parameters:
        - symbol (str): The stock ticker symbol to short sell.
        - qty (int): The number of shares to short sell.
        - limit_price_short (float): The limit price for the short sell order.

        Returns:
        - (bool): True if the short sell order is filled, False otherwise.
        """
        # Place the short sell order after hours
        short_order = self.ALPACA_API.submit_order(
            symbol=symbol,
            qty=qty,
            side='sell',          # Short selling
            type='limit',         # Limit order type
            limit_price=limit_price_short,
            time_in_force='day',  # Day order for extended hours
            extended_hours=True   # Allows after-hours trading
        )

        short_order_id = short_order.id
        
        for _ in range(3600):  # Check every second for up to 60 seconds
            if self.is_order_filled(short_order_id):
                logging.info("Short sell order filled successfully.")
                return True
            time.sleep(1)
        logging.info("Failed to fill short sell order within the time limit.")
        return False


if __name__ == "__main__":
    useless_file=["trading_simulator.log","dividend_trading_results.csv"]
    for file in useless_file:
        try:
            os.remove(file)
        except:
            pass

    logging.basicConfig(filename='trading_simulator.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    #aggiungre il fatto di controllare la mattina che effettivamente l'ordine non sia entrato dopo , eche lo short non sia attivo, moodificare il prezzo di compera quando si cambia, da prezzo serale a prezzo mattutitno etc, anche nella funzione di short magari  !!!
    load_dotenv()
    ALPACA_ENDPOINT='https://paper-api.alpaca.markets/'
    ALPACA_API_KEY=os.getenv('ALPACA_KEY')
    API_SECRET=os.getenv('ALPACA_SECRET')

    simulator = DividendTradingSimulator()
    simulator.run_simulation()
