# src/api_client.py
import requests
import config  # Import dari file config.py

def get_todays_top_gainers():
    """Mengambil list saham Top Gainer hari ini."""
    print("📡 Menghubungi Server: Request Top Gainer...")
    url = f"{config.BASE_URL}/top_gainer"
    params = {"api_key": config.API_KEY}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data['status'] == 'success':
            results = data['data']['results']
            tickers = [item['symbol'] for item in results]
            # Batasi jumlah sesuai config
            return tickers[:config.MAX_STOCKS_TOP_GAINER]
        else:
            print(f"❌ API Error: {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return []

def get_broker_summary(ticker, date_str):
    """Mengambil data broker summary untuk 1 saham & 1 tanggal."""
    url = f"{config.BASE_URL}/{ticker}/broker_summary"
    params = {
        "api_key": config.API_KEY, 
        "date": date_str, 
        "investor": "ALL"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            return "LIMIT"
        else:
            return None
    except Exception as e:
        print(f"Error {ticker}: {e}")
        return None
    


def get_historical_price(ticker, from_date, to_date):
    """Mengambil data harga historis (OHLCV) untuk Target Variable."""
    # Pastikan config sudah di-import di bagian atas file
    url = f"{config.BASE_URL}/{ticker}/historical"
    params = {
        "api_key": config.API_KEY,
        "from": from_date,
        "to": to_date
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data['status'] == 'success':
            return data['data']['results']
        else:
            print(f"❌ API Error ({ticker}): {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return []