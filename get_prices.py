# get_prices.py
import pandas as pd
from datetime import datetime, timedelta
import config
from src import api_client
import os

def run_price_fetcher():
    print("🚀 MEMULAI DOWNLOAD DATA HARGA (OHLCV)")
    print("======================================")
    
    # 1. Tentukan Target Saham
    # Mengambil list dari config.py (baik itu TARGET_TICKERS atau WATCHLIST)
    target_tickers = getattr(config, 'TARGET_TICKERS', [])
    if not target_tickers:
        target_tickers = getattr(config, 'WATCHLIST', [])

    print(f"🎯 Target: {len(target_tickers)} Saham")
    
    # 2. Tentukan Rentang Waktu (1 Tahun ke Belakang)
    # Format API: YYYY-MM-DD
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    print(f"📅 Periode Data: {from_date} s/d {to_date}")
    
    all_prices = []
    
    # 3. Loop Request (Ingat: 1 Request = 1 Tahun Data)
    for ticker in target_tickers:
        print(f"⏳ Fetching {ticker}...", end="")
        
        # Panggil fungsi API (Pastikan src/api_client.py sudah ada fungsi get_historical_price)
        # Sesuai update script sebelumnya
        results = api_client.get_historical_price(ticker, from_date, to_date)
        
        if results:
            # Parsing JSON sesuai struktur yang Anda kirim
            for item in results:
                row = {
                    'ticker': item.get('symbol'), # Pakai 'symbol' dari JSON
                    'date': item.get('date'),
                    'open': item.get('open'),
                    'high': item.get('high'),
                    'low': item.get('low'),
                    'close': item.get('close'),   # <--- INI TARGET UTAMA KITA
                    'volume': item.get('volume')
                }
                all_prices.append(row)
            print(f"✅ OK ({len(results)} hari)")
        else:
            print("⚠️ Kosong/Gagal")
            
    # 4. Simpan ke Excel
    if all_prices:
        os.makedirs("data/raw", exist_ok=True)
        filename = "data/raw/historical_prices_OHLC.xlsx"
        
        df = pd.DataFrame(all_prices)
        
        # Pastikan tidak ada duplikat
        df = df.drop_duplicates(subset=['ticker', 'date'])
        
        # Sortir biar rapi
        df = df.sort_values(by=['ticker', 'date'], ascending=[True, True])
        
        df.to_excel(filename, index=False)
        print(f"\n💾 SUKSES! Data Harga tersimpan di: {filename}")
        print("Tugas 'Tabel B' selesai. Sekarang kita punya Target Variable.")
    else:
        print("\n❌ Gagal. Tidak ada data yang tersimpan.")

if __name__ == "__main__":
    run_price_fetcher()