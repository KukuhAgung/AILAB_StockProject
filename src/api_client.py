# src/api_client.py
import requests
import config
import time

def get_headers():
    return {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json"
    }

def get_broker_summary(ticker, from_date, to_date):
    url = f"{config.BASE_URL}/summary/stock/{ticker}"
    params = {
        "from": from_date,
        "to": to_date,
        "investor": config.DEFAULT_INVESTOR,
        "market": config.DEFAULT_MARKET
    }
    
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=config.TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            print(f"401 UNAUTHORIZED: Token Expired!")
            return "UNAUTHORIZED"
        elif resp.status_code == 429:
            print(f"Rate Limit Hit for {ticker}!")
            time.sleep(5)
            return "LIMIT"
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Connection Error {ticker}: {e}")
        return None

def get_inventory_chart(ticker, from_date, to_date, scope='vol'):
    url = f"{config.BASE_URL}/inventory-chart/stock/{ticker}"
    params = {
        "from": from_date,
        "to": to_date,
        "scope": scope,
        "investor": config.DEFAULT_INVESTOR,
        "market": config.DEFAULT_MARKET
    }
    
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=config.TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            print(f"401 UNAUTHORIZED: Token Expired!")
            return "UNAUTHORIZED"
        elif resp.status_code == 429:
            print(f"Rate Limit Hit for {ticker}!")
            time.sleep(5)
            return "LIMIT"
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Inventory Error {ticker}: {e}")
        return None

def get_shareholder_number(ticker):
    url = f"{config.BASE_URL}/shareholder/number/{ticker}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=config.TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            print(f"401 UNAUTHORIZED: Token Expired!")
            return "UNAUTHORIZED"
        elif resp.status_code == 429:
            print(f"Rate Limit Hit for {ticker}!")
            time.sleep(5)
            return "LIMIT"
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Shareholder Error {ticker}: {e}")
        return None

def get_historical_price_bulk(ticker, from_date, to_date):
    url = f"{config.BASE_URL}/chart/stock/{ticker}"
    params = {"from": from_date, "to": to_date}
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=config.TIMEOUT)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            print(f"401 UNAUTHORIZED: Token Expired!")
            return "UNAUTHORIZED"
        elif resp.status_code == 429:
            print(f"Rate Limit Hit for {ticker}!")
            time.sleep(5)
            return "LIMIT"
        else:
            print(f"Error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Price Error {ticker}: {e}")
        return None