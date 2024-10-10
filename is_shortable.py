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
from google.protobuf import descriptor_pool, message_factory, descriptor_pb2


from dotenv import load_dotenv
import os

load_dotenv()
ALPACA_ENDPOINT='https://paper-api.alpaca.markets/'
ALPACA_API_KEY=os.getenv('ALPACA_KEY')
API_SECRET=os.getenv('ALPACA_SECRET')
ALPACA_API=tradeapi.REST(ALPACA_API_KEY, API_SECRET, ALPACA_ENDPOINT, api_version='v2') 


def is_easy_to_short( symbol):
    asset = ALPACA_API.get_asset(symbol)
    try:
        if asset.easy_to_borrow:
            return True
        else:
            return False
    except:
        return False

print(is_easy_to_short("CIO"))