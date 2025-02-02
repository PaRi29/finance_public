import threading
import time
import json
import base64
import logging
import os
import pytz
import websocket
import pandas as pd
import re
from datetime import datetime, timedelta
from pytz import timezone
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

logging.basicConfig(filename='price_finder.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class YahooFinanceWebSocket:
    def __init__(self):
        self.stock_data = pd.read_csv("stock_to_buy.csv")
        self.date_number = datetime.now(pytz.timezone('Europe/Rome')).strftime('%b %d, %Y')
        self.symbol = self.get_stock_info()
        self.current_price = None
        self.stop_simulation = False
        self.pricing_data_message = self.create_pricing_data_message()
        self.file_path = os.path.join(os.path.dirname(__file__), "..", "assets", "prices.json")
        self._prepare_file()
        self.thread = None
        self.ws = None  # Will hold the WebSocketApp instance

    def _prepare_file(self):
        """Ensure the directory and clean the file for storing prices."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w') as f:
            json.dump({}, f)

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
        factory = message_factory.GetMessageClass(file_descriptor.message_types_by_name['PricingData'])
        return factory

    def decode_protobuf_message(self, base64_message):
        try:
            decoded_bytes = base64.b64decode(base64_message)
            message = self.pricing_data_message()
            message.ParseFromString(decoded_bytes)
            return message
        except Exception as e:
            logging.exception(f"Failed to decode Protobuf message: {e}")
            return None

    def save_price_to_file(self, price):
        """Save the price data to a local JSON file."""
        try:
            with open(self.file_path, 'r+') as f:
                data = json.load(f)
                data[self.symbol] = {"price": price, "timestamp": int(time.time())}
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()
            logging.info(f"Price saved to file: {self.file_path}")
        except Exception as e:
            logging.exception(f"Failed to save price to file: {e}")

    def connect_to_yahoo(self):
        """Connect to the WebSocket and process messages."""
        BASE_URL = 'wss://streamer.finance.yahoo.com'

        def on_message(ws, message):
            if self.stop_simulation:
                ws.close()
                return

            decoded_data = self.decode_protobuf_message(message)
            if decoded_data and decoded_data.id == self.symbol:
                self.current_price = decoded_data.price
                logging.info(f"Current price for {self.symbol}: {self.current_price}")
                self.save_price_to_file(self.current_price)

        def on_error(ws, error):
            if not self.stop_simulation:
                logging.error(f"WebSocket error: {error}")

        def on_close(ws, close_status_code, close_msg):
            logging.info("WebSocket connection closed.")

        def on_open(ws):
            logging.info(f"Connected to Yahoo Finance WebSocket for {self.symbol}.")
            subscribe_message = {"subscribe": [self.symbol]}
            ws.send(json.dumps(subscribe_message))

        while not self.stop_simulation:
            try:
                # Create the WebSocket and store it in self.ws
                self.ws = websocket.WebSocketApp(
                    BASE_URL,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                self.ws.on_open = on_open
                # Run the WebSocket loop. This call is blocking.
                self.ws.run_forever()
            except Exception as e:
                if not self.stop_simulation:
                    logging.exception(f"Error in WebSocket connection: {e}. Reconnecting in 10 seconds...")
                    time.sleep(10)

    def start(self):
        """Start the WebSocket client in a separate thread."""
        self.stop_simulation = False
        if self.symbol is None:
            logging.warning("No valid symbol found. The thread will not be started.")
            return
        self.thread = threading.Thread(target=self.connect_to_yahoo)
        self.thread.start()

    def stop(self):
        """Stop the WebSocket client."""
        self.stop_simulation = True
        # Force the WebSocket to close if it exists.
        if self.ws is not None:
            self.ws.close()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()

    def get_stock_info(self):
        stock_info = self.stock_data[self.stock_data['Date'] == self.date_number]
        if stock_info.empty:
            return None
        stock_info = stock_info.iloc[0]
        stock_name = stock_info['Stock']
        try:
            stock_name = re.search(r'\((.*?)\)', stock_name).group(1)
        except Exception:
            pass
        return stock_name

    @staticmethod
    def wait_until_start():
        """Wait until 9:58 AM Italian time."""
        italy = timezone("Europe/Rome")
        now = datetime.now(italy)
        start_time = now.replace(hour=9, minute=58, second=0, microsecond=0)
        if now > start_time:
            start_time += timedelta(days=1)
        sleep_time = (start_time - now).total_seconds()
        logging.info(f"Waiting until start time (sleeping for {sleep_time} seconds)...")
        time.sleep(sleep_time)

    @staticmethod
    def stop_at_end():
        """Stop at the designated end time."""
        italy = timezone("Europe/Rome")
        now = datetime.now(italy)
        stop_time = now.replace(hour=11, minute=58, second=0, microsecond=0)
        if now > stop_time:
            logging.info("Stop time already passed.")
            return True
        sleep_time = (stop_time - now).total_seconds()
        logging.info(f"Will stop at end time (sleeping for {sleep_time} seconds)...")
        time.sleep(sleep_time)
        return True


if __name__ == "__main__":
    client = YahooFinanceWebSocket()

    try:
        YahooFinanceWebSocket.wait_until_start()
        client.start()
        YahooFinanceWebSocket.stop_at_end()
    finally:
        logging.info("Stopping the WebSocket client...")
        client.stop()
