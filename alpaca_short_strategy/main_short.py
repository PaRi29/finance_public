import datetime
import requests
import csv
from pathlib import Path
import time
import pandas as pd
import pytz
import logging
from bs4 import BeautifulSoup
import re
import alpaca_trade_api as tradeapi
import asyncio
import websockets
import json
import base64
import os
from google.protobuf import descriptor_pool, message_factory, descriptor_pb2
from dotenv import load_dotenv



class DividendTradingSimulator:
    def __init__(self, ALPACA_API_KEY,API_SECRET,ALPACA_ENDPOINT, simulation_days=30, commission=0, short_borrow_rate=0.003):
        self.ALPACA_API=tradeapi.REST(ALPACA_API_KEY, API_SECRET, ALPACA_ENDPOINT, api_version='v2')  
        self.budget = float(self.ALPACA_API.get_account().equity)- 2000
        logging.info(self.budget)
        self.simulation_days = simulation_days
        self.current_simulation_day = 0
        self.transactions = []
        self.italy_tz = pytz.timezone('Europe/Rome')
        self.stock_to_sell = None
        self.sell_price=0
        self.buy_price=0

        self.has_pre = True
        self.dividend_per_action = 0
        self.tomorrow_date_number = 0
        self.stock_data = pd.read_csv("stock_to_buy.csv")
        self.commission = commission
        self.short_borrow_rate = short_borrow_rate
        self.short_commission = 0
        self.short_close_commission = 0
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

        self.current_price = None
        self.pricing_data_message = self.create_pricing_data_message()
        self.stop_simulation = False  # Flag to stop the simulation
        self.tax_rate = 0.27  # 27% tax rate
        self.filled_price = None

    def run_simulation(self):
        while self.current_simulation_day < self.simulation_days:
            start_time = self.get_next_time(hour=20, minute=30)
            self.telegram_bot_sendtext("start_test")
            
            self.sleep_until(start_time)
            logging.info(f"Giorno {self.current_simulation_day + 1}")
            self.telegram_bot_sendtext(f"Giorno {self.current_simulation_day + 1}")


            self.stock_data = pd.read_csv("stock_to_buy.csv")
            self.tomorrow_date_number = (datetime.datetime.now(self.italy_tz) + datetime.timedelta(days=1)).strftime('%b %d, %Y')
            stock_info = self.get_stock_info_for_tomorrow()
            
            if stock_info is None:
                if datetime.datetime.now(self.italy_tz).weekday() == 4:  # Venerdì
                    logging.info("Nessuno stock da shortare per domani e oggi è venerdì. shortando l'azione di lunedì...")
                    self.telegram_bot_sendtext("Nessuno stock da shortare per domani e oggi è venerdì. shortando l'azione di lunedì...")
                    self.tomorrow_date_number = (datetime.datetime.now(self.italy_tz) + datetime.timedelta(days=3)).strftime('%b %d, %Y')
                    stock_info = self.get_stock_info_for_tomorrow()

                    if stock_info is None:
                        logging.info("Nessuno stock disponibile per lunedì. Aspettando il giorno successivo...")
                        self.telegram_bot_sendtext("Nessuno stock disponibile per lunedì. Aspettando il giorno successivo...")
                        time.sleep(23 * 3600 *3)  # Dorme per un giorno
                        self.current_simulation_day += 3
                        continue
                else:
                    logging.info("Nessuno stock da shortare domani. Aspettando il giorno successivo...")
                    self.telegram_bot_sendtext("Nessuno stock da shortare domani. Aspettando il giorno successivo...")
                    time.sleep(23 * 3600)  # Dorme per un giorno
                    self.current_simulation_day += 1
                    continue

            self.stock_to_sell, price_, self.dividend_per_action, self.has_pre = stock_info
            close_market_time=self.get_next_time(hour=1, minute=59)
            self.sleep_until(close_market_time)

            self.last_price = float(self.get_stock_price(self.stock_to_sell))

            self.telegram_bot_sendtext(self.last_price)
            logging.info(f"{self.stock_to_sell}, {self.last_price}, {self.dividend_per_action}, {self.has_pre}")

            if datetime.datetime.now(self.italy_tz).weekday() != 5: 
                sell_time = self.get_next_time(hour=10, minute=0)
            elif datetime.datetime.now(self.italy_tz).weekday() == 5: 
                sell_time = self.get_next_time(hour=10, minute=0) + datetime.timedelta(days=2)

            logging.info(f"In attesa fino alle {sell_time} per la vendita...")
            self.sleep_until(sell_time)

            
            no_hope_time = self.get_next_time(hour=10, minute=59)
            while datetime.datetime.now(self.italy_tz) < no_hope_time:
                if self.is_easy_to_short(self.stock_to_sell):
                    break
                time.sleep(0.35)

            try:
                self.sell_price = float(self.get_stock_price(self.stock_to_buy))
            except:
                self.sell_price = 10

            shares_sold = self.budget // (self.sell_price)
            limit_price= self.sell_price*0.99
            rounded_limit_price = round(limit_price, 2)

            q_ = self.short_sell_pre_hours(self.stock_to_sell, shares_sold, rounded_limit_price)
            if q_:
                self.filled_price = float(q_)
            else:
                self.telegram_bot_sendtext("la vendita allo scoperto giornaliera non ha funzionato")
                self.current_simulation_day += 1
                logging.info("sleeping poche hours")
                time.sleep(60*60*3)
                continue

            logging.info(f"vendendo {shares_sold} azioni di {self.stock_to_sell} a ${self.filled_price:.2f} alle {sell_time}")
            self.telegram_bot_sendtext(f"Vendendo {shares_sold} azioni di {self.stock_to_sell} a ${self.filled_price:.2f} alle {sell_time}")

            target_time = self.get_next_time(hour=15, minute=32)#in ogni caso dorme fino alle 15:30 tanto lo short è già iniziato 
            self.sleep_until(target_time)


            logging.info(f"In attesa fino alle {target_time} per la vendita...")
            asyncio.run(self.run_short_selling(self.stock_to_sell,self.last_price,shares_sold))

            logging.info(f"comprando {shares_sold} azioni di {self.stock_to_sell} a ${self.buy_price:.2f} alle {sell_time}")
            self.telegram_bot_sendtext(f"comprando {shares_sold} azioni di {self.stock_to_sell} a ${self.buy_price:.2f} alle {sell_time}")

            time.sleep(600)
            self.current_simulation_day += 1
            prev_budget=self.budget

            self.budget = float(self.ALPACA_API.get_account().equity)- 2000
            profit_loss= self.budget-prev_budget

            transaction = {
                "day": self.current_simulation_day,
                "stock": self.stock_to_sell,
                "shares": shares_sold,
                "sell_price": self.filled_price,
                "buy_price": self.buy_price,
                "profit_loss": profit_loss,
                "budget": self.budget,
            }

            self.transactions.append(transaction)
            
            logging.info(f"Profitto/Perdita: ${profit_loss:.2f}")
            logging.info(f"Nuovo budget: ${self.budget:.2f}")
            logging.info("---")

            day_summary = (
                "\n--- Riepilogo giornaliero ---\n"
                f"Giorno: {self.current_simulation_day}\n"
                "==================================="
            )
            portfolio_summary = (
                f"stock:  {self.stock_to_sell}\n"
                f"prezzo vi vendita: ${self.filled_price:.2f}\n"
                f"prezzo di acquisto: ${self.buy_price:.2f}\n"
                f"Profitto/Perdita: ${profit_loss:.2f}\n"
                f"Totale Portafoglio: ${self.budget:.2f}\n"
                "==================================="
            )
            self.telegram_bot_sendtext("===================================")
            self.telegram_bot_sendtext(day_summary)
            self.telegram_bot_sendtext(portfolio_summary)
            self.telegram_bot_sendtext("===================================")


        total_profit_loss = self.budget - 3000  # 2500 è il budget iniziale
        logging.info("\n--- Riepilogo finale ---")
        logging.info(f"Bilancio P/L: ${total_profit_loss:.2f}")

        self.telegram_bot_sendtext("\n--- Riepilogo finale ---")
        self.telegram_bot_sendtext(f"Bilancio P/L: ${total_profit_loss:.2f}")
        logging.info("\n")

    def get_stock_price(self, tiker):
        url = "https://api.nasdaq.com/api/quote/"+tiker+"/info?assetclass=stocks"
        payload = {}
        headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7,en-GB;q=0.6',
        'origin': 'https://www.nasdaq.com',
        'priority': 'u=1, i',
        'referer': 'https://www.nasdaq.com/',
        'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        #'Cookie': 'ak_bmsc=DEB43FB40B85B2785EF5A5C447453225~000000000000000000000000000000~YAAQSX4ZuMyKA5qTAQAAMR13thphIDapuahw3uBVXsCwAdSn25qP7uboUcm/JxLVYtN44x5/HwvWOMLGvCTuuRMo24xY2sIrt7B1USF565klavME/yN5DwWn++3WfQfRGgq+ayteyxx/Pgre/sitdxvUU/WqRHAPLTAiAtgmBLjNLXfhJnWndN11X/o6xtVvb4SRvIN++KC00h8Mm8XBojI/DB7T1kv9vKqA0FITb+thFAe9LDKi/4KrlYIQPypi6DDKbuDqSuU6+0BLBz3LL4fgXSURTPRaM8s/X9jezaM83yNL8/GOTKYkhKqx4dlIdHVIWVAAb3Bi+tafjFYVbVnGkWv06IeoSw==; bm_sv=5F7112C9BD34601BE7A9238A29B6B470~YAAQSX4ZuNWMA5qTAQAA+UJ3thrNjluK0cxdMBGqQWdPP5XdE70i1eB8nMLcD9rgGN7JrS0TILiD8Jhp2N1DfezcZnhNt8osfwmFA/ORrh/NPu8v2pxz8+TKevTHYrQzs9LBZhIkf/4yNJlz4jZRN15/wvan1zJItied+3VX2TrYAhgHrFRf8hrnFZDYcysNL9wepZlRbIzXrtN6Dgg1q/xh9XFln7y//k16H6JDZVssW6bpvYER9gl4CFUzgi/m~1; akaalb_ALB_Default=~op=ao_api__east1:ao_api_east1|~rv=34~m=ao_api_east1:0|~os=ff51b6e767de05e2054c5c99e232919a~id=a6a87be6083abadbf68a65760892cbd0'
        }
        try:
            response = requests.request("GET", url, headers=headers, data=payload)
            response.raise_for_status()  # Raise an error for bad responses
            data = json.loads(response.text) 
            return(float(str(data["data"]["primaryData"]["lastSalePrice"]).replace("$","")))
        except :
            return None  # Return None or handle the error as needed



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
        stop_gain = -0.9 * self.dividend_per_action / self.sell_price
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
        self.buy_price = self.current_price  # Usa il prezzo corrente per chiudere la posizione
        close_price=self.current_price*1.002
        self.close_position(symbol,close_price)
        short_profit = (initial_price - self.buy_price) * shares_sold - borrow_cost - self.short_commission - self.short_close_commission
        # Applica tasse sui profitti
        if short_profit > 0:
            short_profit *= (1 - self.tax_rate)

        logging.info(f"Profit from short selling {symbol}: {short_profit:.2f}")
        return short_profit
    

    def close_position(self, symbol, price):
        try:
            position = self.ALPACA_API.get_position(symbol)

            qty = abs(int(position.qty))
            if position.side == 'long':
                # Close the long position by selling the shares
                self.ALPACA_API.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',          # Short selling
                    type='limit',         # Limit order type
                    limit_price=price,
                    time_in_force='gtc')

                logging.info(f'Closed long position for {symbol}.')

            elif position.side == 'short':
                # Close the short position by buying the shares
                self.ALPACA_API.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',          # Short selling
                    type='limit',         # Limit order type
                    limit_price=price,
                    time_in_force='gtc')

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
    def is_order_filled(self, order_id):
        order = self.ALPACA_API.get_order(order_id)
        return order.status == 'filled'

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

    def get_stock_info_for_tomorrow(self):
        stock_info = self.stock_data[self.stock_data['Date'] == self.tomorrow_date_number]
        if stock_info.empty:
            return None
        stock_info = stock_info.iloc[0]
        stock_name = stock_info['Stock']
        try:
            stock_name = re.search(r'\((.*?)\)', stock_name).group(1)
        except: 
            pass
        return stock_name, stock_info['Price'], stock_info['Yield Price'], stock_info['Has Pre']
    
    def get_next_time(self, hour, minute):
        now = datetime.datetime.now(self.italy_tz)
        next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_time <= now:
            next_time += datetime.timedelta(days=1)
        return next_time
    
    def is_easy_to_short(self, symbol):
        asset = self.ALPACA_API.get_asset(symbol)
        try:
            if asset.easy_to_borrow:
                return True
            else:
                return False
        except:
            return False
            
    def sleep_until(self, target_time):
        now = datetime.datetime.now(self.italy_tz)
        wait_time = (target_time - now).total_seconds()
        if wait_time > 0:
            time.sleep(wait_time)

    def telegram_bot_sendtext(self, messages):
        send_text = "https://api.telegram.org/bot"+self.TELEGRAM_BOT_TOKEN+"/sendMessage?chat_id="+self.TELEGRAM_CHAT_ID+"&text={}".format(str(messages))
        requests.get(send_text)
        
    def short_sell_pre_hours(self, symbol, qty, limit_price_short):
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
                filled_order = self.ALPACA_API.get_order(short_order_id)  # Fetch the filled order details
                logging.info(f"Short sell order filled successfully at {filled_order.filled_avg_price}.")
                return filled_order.filled_avg_price  # Return the filled price
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
    load_dotenv()
    ALPACA_ENDPOINT='https://paper-api.alpaca.markets/'
    ALPACA_API_KEY=os.getenv('ALPACA_KEY')
    API_SECRET=os.getenv('ALPACA_SECRET')


    simulator = DividendTradingSimulator(ALPACA_API_KEY=ALPACA_API_KEY, ALPACA_ENDPOINT=ALPACA_ENDPOINT,API_SECRET=API_SECRET)
    simulator.run_simulation()
