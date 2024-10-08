import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import yfinance as yf
import time
import platform

def get_tomorrow_date():
    tomorrow = datetime.now().date() + timedelta(days=1)
    if platform.system() == 'Windows':
        return tomorrow.strftime("%#m/%#d/%Y")
    else:
        return tomorrow.strftime("%-m/%-d/%Y")

def scrape_ex_dividend_data():
    url = "https://www.marketbeat.com/dividends/ex-dividend-calendar/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    tbody = soup.find('tbody')
    
    tomorrow = get_tomorrow_date()
    print(f"Filtering for ex-dividend date: {tomorrow}")
    
    data = []
    total_rows = 0
    matching_rows = 0

    for row in tbody.find_all('tr'):
        total_rows += 1
        ticker_cell = row.find('td', {'data-clean': True})
        if ticker_cell:
            ticker = ticker_cell.find('div', {'class': 'ticker-area'}).get_text(strip=True)
            company = ticker_cell.find('div', {'class': 'title-area'}).get_text(strip=True)
        else:
            continue

        dividend = row.find_all('td')[2].get_text(strip=True)
        ex_div_date = row.find_all('td')[4].get_text(strip=True)
        
        print(f"Processing: {ticker}, Ex-Date: {ex_div_date}")
        
        if ex_div_date == tomorrow:
            matching_rows += 1
            data.append({
                "Ticker": ticker,
                "Company": company,
                "Dividend": dividend,
                "Ex-Date": ex_div_date
            })

    print(f"Total rows processed: {total_rows}")
    print(f"Matching rows found: {matching_rows}")
    return data

def save_to_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Data saved to {filename}")

def update_dividend_percentages(data):
    a=1
    for stock in data:
        print("stock n. "+str(a) +" out of: " +str(len(data)))
        ticker = stock['Ticker']
        try:
            yf_ticker = yf.Ticker(ticker)
            current_price = yf_ticker.info.get('currentPrice')
            
            if current_price:
                dividend_amount = float(stock['Dividend'].replace('$', ''))
                dividend_percentage = (dividend_amount / current_price) * 100
                
                stock['Current Price'] = f"${current_price:.2f}"
                stock['Dividend Percentage'] = f"{dividend_percentage:.2f}%"
            else:
                print(f"Could not fetch price for {ticker}")
            
            time.sleep(0.5)
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
        a=a+1
    return data

def main():
    current_date = datetime.now().strftime("%Y-%m-%d")
    initial_filename = f"ex_dividend_data_{current_date}.json"
    updated_filename = f"updated_ex_dividend_data_{current_date}.json"

    # Scrape initial data
    initial_data = scrape_ex_dividend_data()
    if initial_data:
        save_to_json(initial_data, initial_filename)

        # Update with dividend percentages
        updated_data = update_dividend_percentages(initial_data)
        save_to_json(updated_data, updated_filename)
    else:
        print("No matching data found for tomorrow's ex-dividend date.")

if __name__ == "__main__":
    main()
