import csv
from bs4 import BeautifulSoup
import requests
import pandas as pd
import json
import re
from datetime import datetime, timedelta
import yfinance as yf  # Add this import
import numpy as np  # Add this import
import time
import cloudscraper
from dotenv import load_dotenv
import os


load_dotenv()
ALPACA_ENDPOINT='https://paper-api.alpaca.markets/'
ALPACA_API_KEY=os.getenv('ALPACA_KEY')
API_SECRET=os.getenv('ALPACA_SECRET')


class DividendDataExtractor:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.all_data = []


    def get_dividend_data(self, timestamp):
        scraper = cloudscraper.create_scraper()
        url = "https://www.investing.com/dividends-calendar/Service/getCalendarFilteredData"
        payload = f"currentTab=nextWeek&limit_from=1&submitFilters=0&last_time_scope={timestamp}&byHandler=true"
        headers = {
  'accept': '*/*',
  'accept-language': 'en-US,en;q=0.9,it-IT;q=0.8,it;q=0.7,en-GB;q=0.6',
  'content-type': 'application/x-www-form-urlencoded',
  'cookie': 'page_equity_viewed=0; udid=e02c0e024250fc5f93bc409900c735e5; video_location_variant=2; _fbp=fb.1.1724862546728.52972773454275358; __eventn_id=e02c0e024250fc5f93bc409900c735e5; __eventn_uid=259066576; _lr_env_src_ats=false; _au_1d=AU1D-0100-001718809544-E12TUGUO-R0NJ; _hjSessionUser_174945=eyJpZCI6ImZmMTgzNDI1LTkwZTEtNTk2Mi05MDkyLTNhZGM4Yjg4YjdiNSIsImNyZWF0ZWQiOjE3MjQ4NjI1NDY5MDIsImV4aXN0aW5nIjp0cnVlfQ==; _pbjs_userid_consent_data=3524755945110770; r_p_s_n=1; finboxio-production:refresh=930fb67e-8a4e-45bd-be8f-e2faa880646c; finboxio-production:refresh.sig=Y4OfQAWEUHIdZryY10b-K_Oq0LA; finboxio-production:jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyNjAwMzI4LCJ2aXNpdG9yX2lkIjoidi02NGJlODk1NjM5NDQiLCJmaXJzdF9zZWVuIjoiMjAyNC0wNS0yOFQxNTo0OTo1OC40MDZaIiwiY2FwdGNoYV92ZXJpZmllZCI6ZmFsc2UsIm11c3RfcmV2ZXJpZnkiOmZhbHNlLCJwcmV2aWV3X2FjY2VzcyI6eyJhc3NldHNfdmlld2VkIjpbIk5ZU0U6RVVSTiJdLCJhc3NldHNfbWF4Ijo1LCJ2YWxpZF91bnRpbCI6IjIwMjQtMDUtMjlUMDM6NDk6NTguMDAwWiJ9LCJyb2xlcyI6WyJ1c2VyIiwiaW52ZXN0aW5nIl0sImJvb3N0cyI6W10sImFzc2V0cyI6W10sInJlZ2lvbnMiOltdLCJzY29wZXMiOlsicm9sZTp1c2VyIiwicm9sZTppbnZlc3RpbmciXSwiZm9yIjoiMjEzLjQ1LjI1LjE0MiIsImV4cCI6MTcyNTM5NDk1NiwiaWF0IjoxNzI1Mzk0NjU2fQ.0SGVEKMtRU522VSEHngddahMXVUKGt1C9jnBkHevo7g; finboxio-production:jwt.sig=WQxT1IJXwhakkVmJBrd_vlBWGp0; usprivacy=1YNN; ccuid=1b3840c3-2f9b-43aa-97e1-e5ae946da066; __eventn_id_usr=%7B%22adFreeUser%22%3A0%2C%22investingProUser%22%3A0%2C%22investingProPremiumUser%22%3A0%7D; hb_insticator_uid=50b50f54-5a72-4912-a2e7-858982636933; _cc_id=bf5d2d58b19dda54f05ef501c7d7cafb; panoramaId=882ee12cec0b0e536b4ce27b01ca185ca02c39db1bd0bb09cbea08bb3b2d8156; panoramaIdType=panoDevice; _au_last_seen_iab_tcf=1727134623827; panoramaId_expiry=1727739430990; adBlockerNewUserDomains=1727219269; cto_bidid=xjDj0l9Vd3FTWGtwUUhPa052S1hHNm5LWHlpQ01QZW4ydzAzYVJmdSUyRlVhTWphZmV5USUyQjIzWjRDeng2RzNwVHg4SjdzNk0wSFNEZ3VDREFISEslMkZqdW5sdGl4JTJCMGI0cWxhTGFvTXpyOXViQk1icHlvJTNE; pbjs-unifiedid=%7B%22TDID%22%3A%227dad01dd-43b6-4bc8-9728-7a59ee9056f3%22%2C%22TDID_LOOKUP%22%3A%22TRUE%22%2C%22TDID_CREATED_AT%22%3A%222024-08-25T14%3A54%3A51%22%7D; __cflb=02DiuGRugds2TUWHMkkPGro65dgYiP187UkW6NQVHvirY; upa=eyJpbnZfcHJvX2Z1bm5lbCI6IjMiLCJtYWluX2FjIjoiNCIsIm1haW5fc2VnbWVudCI6IjIiLCJkaXNwbGF5X3JmbSI6IjExMSIsImFmZmluaXR5X3Njb3JlX2FjX2VxdWl0aWVzIjoiOSIsImFmZmluaXR5X3Njb3JlX2FjX2NyeXB0b2N1cnJlbmNpZXMiOiI0IiwiYWZmaW5pdHlfc2NvcmVfYWNfY3VycmVuY2llcyI6IjMiLCJhY3RpdmVfb25faW9zX2FwcCI6IjAiLCJhY3RpdmVfb25fYW5kcm9pZF9hcHAiOiIxIiwiYWN0aXZlX29uX3dlYiI6IjEiLCJpbnZfcHJvX3VzZXJfc2NvcmUiOiIxMDAifQ%3D%3D; _imntz_error=0; identify_sent=259066576|1727777434593; im_sharedid=72e8eed7-8b31-41a6-ade7-d3408cc0a123; _gid=GA1.2.1181319290.1727691037; pbjs-unifiedid_last=Mon%2C%2030%20Sep%202024%2010%3A10%3A38%20GMT; _lr_sampling_rate=100; upa=eyJpbnZfcHJvX2Z1bm5lbCI6IjMiLCJtYWluX2FjIjoiNCIsIm1haW5fc2VnbWVudCI6IjIiLCJkaXNwbGF5X3JmbSI6IjExMSIsImFmZmluaXR5X3Njb3JlX2FjX2VxdWl0aWVzIjoiOSIsImFmZmluaXR5X3Njb3JlX2FjX2NyeXB0b2N1cnJlbmNpZXMiOiI0IiwiYWZmaW5pdHlfc2NvcmVfYWNfY3VycmVuY2llcyI6IjMiLCJhY3RpdmVfb25faW9zX2FwcCI6IjAiLCJhY3RpdmVfb25fYW5kcm9pZF9hcHAiOiIxIiwiYWN0aXZlX29uX3dlYiI6IjEiLCJpbnZfcHJvX3VzZXJfc2NvcmUiOiIxMDAifQ%3D%3D; comment_notification_259066576=1; Adsfree_conversion_score=2; adsFreeSalePopUpf5bf0d77e6cd1c5e7273fa8b10a171d5=1; gtmFired=OK; PHPSESSID=5s9nalh1u0qjq3edp6f2nsv36e; browser-session-counted=true; user-browser-sessions=10; geoC=IT; accessToken=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Mjc3Mzk5MDksImp0aSI6IjI1OTA2NjU3NiIsImlhdCI6MTcyNzczNjMwOSwiaXNzIjoiaW52ZXN0aW5nLmNvbSIsInVzZXJfaWQiOjI1OTA2NjU3NiwicHJpbWFyeV9kb21haW5faWQiOiIxIiwiQXV0aG5TeXN0ZW1Ub2tlbiI6IiIsIkF1dGhuU2Vzc2lvblRva2VuIjoiIiwiRGV2aWNlVG9rZW4iOiIiLCJVYXBpVG9rZW4iOiJObmhsSkRRN1kydGhKVzlwWXpKaFptSTZOVzQwTlRRd1ptSnVhbWRtWm5BekoySnNaRE0zY1RZNVBuQmlZVEFzUHpjMk1HRm1ZVEl5WWpRNVlURnVQVFkwWldBME5tTnNZVDl2TW1NMVlXUmlZVFZ1TkdJMFpHWm1iamhuTm1adU16eGlNbVEzTjJjMk5UNW1ZajB3UFQ4dE5pcGhKV0Z3TW1BMFpHRWdiaWsyT1dVa05HUmpPV0ZoYnpGak1tRnFZbVUxYkRSZ05EZG1ZMjVzWjJCbWZqTjQiLCJBdXRobklkIjoiIiwiSXNEb3VibGVFbmNyeXB0ZWQiOmZhbHNlLCJEZXZpY2VJZCI6IiIsIlJlZnJlc2hFeHBpcmVkQXQiOjE3MzAyNTYzMDl9.twkay8e7Y1QrYubx4JBcn-SJ0DMBFBT-OAC1zrQr4T0; proscore_card_opened=1; __gads=ID=09ee4bed789a1a58:T=1724862556:RT=1727736315:S=ALNI_Ma-UUCLQPM19O88H5eVlJ5vGih0aw; _lr_retry_request=true; SideBlockUser=a%3A2%3A%7Bs%3A10%3A%22stack_size%22%3Ba%3A1%3A%7Bs%3A11%3A%22last_quotes%22%3Bi%3A8%3B%7Ds%3A6%3A%22stacks%22%3Ba%3A1%3A%7Bs%3A11%3A%22last_quotes%22%3Ba%3A8%3A%7Bi%3A0%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A6%3A%22960636%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A26%3A%22%2Fequities%2Fofs-capital-corp%22%3B%7Di%3A1%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A5%3A%2221248%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A17%3A%22%2Fequities%2Feni-spa%22%3B%7Di%3A2%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A7%3A%221097399%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A40%3A%22%2Fequities%2Fbain-capital-specialty-finance%22%3B%7Di%3A3%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A5%3A%2232315%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A33%3A%22%2Fequities%2Fenergetica-minas-gerais%22%3B%7Di%3A4%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A5%3A%2224369%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A35%3A%22%2Fequities%2Fgladstone-investment-corp%22%3B%7Di%3A5%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A5%3A%2248370%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A26%3A%22%2Fequities%2Fcherry-hill-mort%22%3B%7Di%3A6%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A5%3A%2220753%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A29%3A%22%2Fequities%2Fgamco-investors-inc%22%3B%7Di%3A7%3Ba%3A3%3A%7Bs%3A7%3A%22pair_ID%22%3Bs%3A5%3A%2239297%22%3Bs%3A10%3A%22pair_title%22%3Bs%3A0%3A%22%22%3Bs%3A9%3A%22pair_link%22%3Bs%3A37%3A%22%2Fequities%2Ftwo-harbors-investment-corp%22%3B%7D%7D%7D%7D; AMZN-Token=v2FweLxhNC9ZMkhqclBkdHNWdHJXU3B6cXdCblZkQWdCaHhXQllyaE1IZEhDOWhYaS93NHZzV2NOenJzR0FIbGk0cGk0d2gwcnZ4dDVCTTU0YUhxdk83SVJ2Y2MrZjcweDZ3SkFJSEk1VmVYK0tUWDlHci9GYzgvaHd3ZmlMdUxhRVlyQ1B3czZBWFB1NFF4Y0U4VGNTbFluVnlhZHcwc3hwTldZVmxWL2dPZ2N3eW1ISkxLdmRlUTEzT2hLYytnPWJrdgFiaXZ4JE91Ky92UmNqNzcrOTc3Kzk3Nys5NzcrOTc3Kzl4cDd2djcwPf8=; _ga_FVWZ0RM4DH=GS1.1.1727736305.61.1.1727736333.32.0.0; gcc=CA; gsc=ON; smd=e02c0e024250fc5f93bc409900c735e5-1727738579; __cf_bm=FgPhHiOIU5mgJU1fp97AKFORlCc5i0ihJS1kd6eUBt4-1727738580-1.0.1.1-PSxvsnGfgfFodD2n.cvXSVZh2OchROp3tZM63xE2cly2_wXSinfj4sT2BDBHBZHI0dbUg14AfO_kioa6maixhyM0M_PZy3xvEuqGyIRoeLU; lifetime_page_view_count=137; _hjSession_174945=eyJpZCI6Ijc4MDQ1N2VlLWIzZDQtNGY0Ny1hM2EwLTFhMGYzMzhhYmZhMiIsImMiOjE3Mjc3Mzg1ODE4NDgsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; cf_clearance=wYKhV6uTAJKpSL2zbJDHGuFuyw2tGKOdDefkarYxHqQ-1727738582-1.2.1.1-d7JxcEGBiUt.Qz.5fZmTWiBa9rX9l13w5_Xnfe1lJSDvPituzLx1JCeSGhIERATfiAJdRx3SRQoivx6ut0hwl_viTj0Y2pikFHXgyeUqvxESiRXl0rx7RHUiTGeqyP5zak4Zfwfrg9MmI9kQsStD5HjpurCj2pYDPglVrnE0HjRC0xVsOYc5zZvg0NimBYaS8.B.YrcjPpnfsAWijAwhkvMkHWUD1aUMdl326xSDkqZi.zrqryBXtkfn5unruzD0CP0_bYntsy6ET5.L86bs.0xO8TDgkfSSDWEP28MrCDKbJK.8V2wKCNu6QtbzCJNO9ClqJnbzpa2gMVNGpXuCkpy4biAPb3UmTeRaYtlcD1mL6RF4Ukt0Hj.OP3bevbqsisve6OkP2ADpo.wNdKvpTA; im_sharedid_cst=zix7LPQsHA%3D%3D; dicbo_id=%7B%22dicbo_fetch%22%3A1727738583206%7D; invpc=13; _gat=1; _gat_allSitesTracker=1; _ga_C4NDLGKVMK=GS1.1.1727738582.72.1.1727738590.52.0.0; _ga=GA1.1.307090630.1724862548; page_view_count=13; _hjHasCachedUserAttributes=true; ses_id=MX81dDE%2BPzc0cGBmbz44PzJqZT5hYGJmMzczNzAxYHY0IDE%2FYDdmIDY5PXNmZTYqYmVjYDVrNDQ2NW4xYGFjNjE8NW8xND9iNGBgP28%2BODIya2VvYWJiZzNmMzQwMGA5NGAxNGBnZmM2NT01Zm42PmJwY381cTQlNmRuPmAhYyQxPjV0MWE%2FZTQ0YD5vPzg4Mjdla2FhYmIzMjMyMDBgeDR%2F; nyxDorf=ZWEzY28xNnRhNjo%2FM2c1KTNjYjowNzQoND1vbw%3D%3D; __eoi=ID=81257aebf81e689e:T=1724862556:RT=1727738590:S=AA-AfjZj5ZkGmEOuv5GdyvSjIRgE; cto_bundle=UYLNA19nZTYxZTdraHVyeXd3UnRFQ2RyUm1sM1dNYkg5JTJGUkxqMHlhJTJCTnJ6MG80Y252c2YySERIbjlKdHk1WmN2MVowMiUyQnd1YjFsR2hPUGZ0MndGUmVtTmVEeko2dGJsUkJWcHU2UlY2YUhtOWJyWG9wWlc1dnElMkZJaGFGQWRnWmMzYkJMQXF0dVhyQ2NCZlh1enZoM1JUbHBTUSUzRCUzRA; firstUdid=0; ses_id=Yy0xcDE%2BMTkxdW1rZDU2MT9nNW5mZ2FlYmZgZDMyYHYyJjU7YDdlIzI9aSdvbGV5Mmc3NmZjMGU2Y25gYGFiZmNiMWQxMjFqMTFtNWRjNmc%2FPTVrZjVhZ2I3YGYzNWBpMjw1YGAyZWcyYGkxb2FlODIgNytmIjAhNmRuPmAhYiVjbDFwMWExazExbTNkNDY3P201P2ZgYTZiNmA1MzdgeDJ5; smd=e02c0e024250fc5f93bc409900c735e5-1727738579; udid=e02c0e024250fc5f93bc409900c735e5; PHPSESSID=5s9nalh1u0qjq3edp6f2nsv36e; __cflb=02DiuGRugds2TUWHMkkPGro65dgYiP188GMbpJwW1YMAt; upa=eyJpbnZfcHJvX2Z1bm5lbCI6IjMiLCJtYWluX2FjIjoiNCIsIm1haW5fc2VnbWVudCI6IjIiLCJkaXNwbGF5X3JmbSI6IjExMSIsImFmZmluaXR5X3Njb3JlX2FjX2VxdWl0aWVzIjoiOSIsImFmZmluaXR5X3Njb3JlX2FjX2NyeXB0b2N1cnJlbmNpZXMiOiI0IiwiYWZmaW5pdHlfc2NvcmVfYWNfY3VycmVuY2llcyI6IjMiLCJhY3RpdmVfb25faW9zX2FwcCI6IjAiLCJhY3RpdmVfb25fYW5kcm9pZF9hcHAiOiIxIiwiYWN0aXZlX29uX3dlYiI6IjEiLCJpbnZfcHJvX3VzZXJfc2NvcmUiOiIxMDAifQ%3D%3D',
  'origin': 'https://www.investing.com',
  'priority': 'u=1, i',
  'referer': 'https://www.investing.com/dividends-calendar/',
  'sec-ch-ua': '"Brave";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'sec-gpc': '1',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  'x-requested-with': 'XMLHttpRequest'
}       
        response = scraper.post(url, headers=headers, data=payload)
        print(response.status_code)
        # Parse the JSON response
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            print("JSON decoding failed:", e)
            #print("Response text:", response.text)
            return None  # or handle the error appropriately
        html_content = data['data']
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract the table rows
        rows = soup.find_all('tr')
        frequency_type_allowed=["semi-annual","annual","quarterly","monthly"]
        extracted_data = []

        print(len(rows))
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 4:  # Ensure it's a data row
                country = cols[0].find(
                    'span')['title'] if cols[0].find('span') else ''
                company_element = cols[1].find(
                    'span', class_='earnCalCompanyName middle')
                company = company_element.text.strip() if company_element else ''
                ticker = cols[1].find('a', class_='bold').text.strip(
                ) if cols[1].find('a', class_='bold') else ''
                ex_dividend_date = cols[2].text.strip()
                dividend = cols[3].text.strip()
                frequency = str(cols[4].find(
                    'span')['title']).lower() if cols[4].find('span') else ''
                payment_date = cols[5].text.strip()
                yield_value = cols[6].text.strip()
                if  frequency in frequency_type_allowed:
                    extracted_data.append(
                        [country, company, ticker, ex_dividend_date, dividend, frequency, payment_date, yield_value])
        return extracted_data

    def extract_data(self):
        current_date = self.start_date
        while current_date <= self.end_date:
            timestamp = int(current_date.timestamp())
            print(current_date)
            try:
                weekly_data = self.get_dividend_data(timestamp)
                self.all_data.extend(weekly_data)
            except:
                print("error"+str(current_date))
                time.sleep(60)
                weekly_data = self.get_dividend_data(timestamp)
                self.all_data.extend(weekly_data)

            current_date += timedelta(days=1)

        # Create a DataFrame
        df = pd.DataFrame(self.all_data, columns=[
                          'Country', 'Company', 'Ticker', 'Ex-Dividend Date', 'Dividend', 'Frequency', 'Payment Date', 'Yield'])

        # Clean up the data
        # Remove any remaining HTML tags
        df = df.applymap(lambda x: re.sub(r'<.*?>', '', str(x)))
        df = df.applymap(lambda x: x.strip() if isinstance(
            x, str) else x)  # Strip whitespace

        # Remove duplicates
        df.drop_duplicates(inplace=True)
        df = df[~df['Ticker'].str.isdigit()]
        row_count = len(df)
        print(f'Number of rows: {row_count}')

        df = df[df['Ticker'].apply(self.is_stock_liquid)]
        row_count = len(df)
        print(f'Number of rows: {row_count}')

        df.to_csv('stock_to_buy.csv', index=False)


    def is_stock_liquid(self, ticker):
        time.sleep(0.31)
        headers = {
            'APCA-API-KEY-ID': ALPACA_API_KEY,
            'APCA-API-SECRET-KEY': API_SECRET
        }
        response = requests.get(f'{ALPACA_ENDPOINT}/v2/assets/{ticker}', headers=headers)
        if response.status_code == 200:
            asset_info = response.json()
            shortable = asset_info.get('shortable', False)
            return shortable  # Return only shortable status
        else:
            print(f'Error: {response.status_code}, {response.text}')
            return False  # Return None on error
        

if __name__ == "__main__":
    start_date = datetime(2024, 10, 1)  # Replace with your desired start date
    end_date = datetime(2024, 10, 1)    # Replace with your desired end date

    extractor = DividendDataExtractor(start_date, end_date)
    extractor.extract_data()
