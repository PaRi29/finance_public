

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
import asyncio
import websockets
import json
import base64
from google.protobuf import descriptor_pool, message_factory, descriptor_pb2

#aggiungre il fatto di controllare la mattina che effettivamente l'ordine non sia entrato dopo , eche lo short non sia attivo, moodificare il prezzo di compera quando si cambia, da prezzo serale a prezzo mattutitno etc, anche nella funzione di short magari  !!!
load_dotenv()


class Test():
    def __init__(self, initial_budget=1000, simulation_days=30, commission=1.0, short_borrow_rate=0.003):
        self.dividend_balance = 0
        self.simulation_days = simulation_days
        self.current_simulation_day = 0
        self.transactions = []
        self.italy_tz = pytz.timezone('Europe/Rome')
        self.stock_to_buy = None
        self.has_pre = True
        self.dividend_per_action = 0.6
        self.tomorrow_date_number = 0
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

    
    def prova(self):
        asyncio.run(self.run_short_selling("BMY",53.20,10))

    def calculate_short_profit(self, symbol, initial_price, shares_sold, borrow_cost):
        """Calcola il profitto finale della vendita allo scoperto."""
        if self.current_price is None:
            print(f"Error: No valid current price available for {symbol} at the time of closing.")
            return None

        self.close_price = self.current_price  # Usa il prezzo corrente per chiudere la posizione
        self.close_position(symbol)

        short_profit = (initial_price - self.close_price) * shares_sold - borrow_cost - self.short_commission - self.short_close_commission

        # Applica tasse sui profitti
        if short_profit > 0:
            short_profit *= (1 - self.tax_rate)

        print(f"Profit from short selling {symbol}: {short_profit:.2f}")
        return short_profit

    def close_position(self, symbol):
        print("position of "+str(symbol)+ " closed")

    async def connect_to_yahoo(self, symbol):
        """Connect to Yahoo Finance WebSocket and update self.current_price with feed data."""
        BASE_URL = 'wss://streamer.finance.yahoo.com'
        
        while not self.stop_simulation:  # Loop to handle reconnections
            try:
                async with websockets.connect(BASE_URL) as websocket:
                    print(f"Connected to Yahoo Finance WebSocket for {symbol}.")
                    subscribe_message = {"subscribe": [symbol]}
                    await websocket.send(json.dumps(subscribe_message))

                    while not self.stop_simulation:
                        message = await websocket.recv()
                        decoded_data = self.decode_protobuf_message(message)
                        if decoded_data and decoded_data.id == symbol:
                            self.current_price = decoded_data.price
                            print(f"Current price for {symbol}: {self.current_price}")
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed. Reconnecting in 1 minute...")
                await asyncio.sleep(60)  # Wait 1 minute before trying to reconnect

            except Exception as e:
                print(f"Error in WebSocket connection: {e}. Reconnecting in 1 minute...")
                await asyncio.sleep(60)  # Wait 1 minute before trying to reconnect

    async def simulate_short_selling(self, symbol, initial_price, shares_sold):
        """Simulate short selling monitoring stop loss, stop gain, or market close."""
        borrow_cost = shares_sold * initial_price * self.short_borrow_rate
        stop_gain = -0.5 * self.dividend_per_action / initial_price
        stop_loss = 0.02
        market_close_time = datetime.time(21, 50)

        while not self.stop_simulation:
            current_time = datetime.datetime.now(self.italy_tz).time()

            # Check market close condition
            if current_time >= market_close_time:
                print(f"Market closed at {current_time}, ending simulation.")
                self.stop_simulation = True
                return self.calculate_short_profit(symbol, initial_price, shares_sold, borrow_cost)

            # Wait for current price to be updated
            if self.current_price is None:
                await asyncio.sleep(1)
                continue
            price_change = (self.current_price - initial_price) / initial_price

            # Check stop loss condition
            if price_change >= stop_loss:
                print(f"Stop loss triggered at {self.current_price:.2f}")
                self.stop_simulation = True
                return self.calculate_short_profit(symbol, initial_price, shares_sold, borrow_cost)

            # Check stop gain condition
            if price_change <= stop_gain:
                print(f"Stop gain triggered at {self.current_price:.2f}")
                self.stop_simulation = True
                return self.calculate_short_profit(symbol, initial_price, shares_sold, borrow_cost)

            await asyncio.sleep(1)  # Sleep for a short duration before checking again

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
        return message_factory.GetMessageClass(file_descriptor.message_types_by_name['PricingData'])

    def decode_protobuf_message(self, base64_message):
        try:
            decoded_bytes = base64.b64decode(base64_message)
            message = self.pricing_data_message()
            message.ParseFromString(decoded_bytes)
            return message
        except Exception as e:
            print(f"Failed to decode Protobuf message: {e}")
            return None


test= Test()
test.prova()