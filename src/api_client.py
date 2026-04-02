# src/api_client.py
import requests
import config
import time
import streamlit as st

def get_headers():
    return {
        "Authorization": f"Bearer {st.secrets["API_KEY"]}",
        "Content-Type": "application/json"
    }

def get_broker_summary(ticker, from_date, to_date):
    url = f"{st.secrets["BASE_URL"]}/summary/stock/{ticker}"
    params = {
        "from": from_date,
        "to": to_date,
        "investor": st.secrets["DEFAULT_INVESTOR"],
        "market": st.secrets["DEFAULT_MARKET"]
    }
    
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=st.secrets["TIMEOUT"])
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
    url = f"{st.secrets["BASE_URL"]}/inventory-chart/stock/{ticker}"
    params = {
        "from": from_date,
        "to": to_date,
        "scope": scope,
        "investor": st.secrets["DEFAULT_INVESTORE"],
        "market": st.secrets["DEFAULT_MARKET"]
    }
    
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=st.secrets["TIMEOUT"])
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
    url = f"{st.secrets["BASE_URL"]}/shareholder/number/{ticker}"
    try:
        resp = requests.get(url, headers=get_headers(), timeout=st.secrets["TIMEOUT"])
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
    url = f"{st.secrets["BASE_URL"]}/chart/stock/{ticker}"
    params = {"from": from_date, "to": to_date}
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=st.secrets["TIMEOUT"])
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
    
# --- NEW FUNCTIONS (ULTIMATE HARVESTER) ---

def get_summary_chart(ticker, from_date, to_date, scope='volume'):

    url = f"{st.secrets["BASE_URL"]}/summary-chart/stock/{ticker}"
    params = {
        "from": from_date,
        "to": to_date,
        "scope": scope,
        "market": st.secrets["DEFAULT_MARKET"]
    }
    
    try:
        resp = requests.get(url, headers=get_headers(), params=params, timeout=st.secrets["TIMEOUT"])
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
            # Kadang endpoint ini return 404 jika data kosong (saham baru)
            if resp.status_code != 404:
                print(f"Error Summary Chart {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Foreign Flow Error {ticker}: {e}")
        return None

def get_shareholder_composition(ticker):
    
    url = f"{st.secrets["BASE_URL"]}/shareholder/{ticker}"
    
    try:
        resp = requests.get(url, headers=get_headers(), timeout=st.secrets["TIMEOUT"])
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            return "UNAUTHORIZED"
        elif resp.status_code == 429:
            print(f"Rate Limit Hit for {ticker}!")
            time.sleep(5)
            return "LIMIT"
        else:
            print(f"Error Shareholder Comp {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"Shareholder Comp Error {ticker}: {e}")
        return None