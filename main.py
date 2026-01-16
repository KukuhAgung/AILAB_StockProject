# main.py
import pandas as pd
import time
from datetime import datetime
import os

# Import modul buatan kita sendiri
import config
from src import api_client, data_processor

def run_harvester():
    print("🚀 MEMULAI PROGRAM BANDARMOLOGY HARVESTER")
    print("=========================================")
    
    # 1. Tentukan Target Saham (Pilih salah satu metode)
    # Metode A: Pakai Watchlist Manual di config
    # target_tickers = config.WATCHLIST 
    
    # Metode B: Otomatis cari Top Gainer
    target_tickers = api_client.get_todays_top_gainers()
    
    if not target_tickers:
        print("⚠️ Tidak ada saham target. Program berhenti.")
        return

    print(f"🎯 Target Hari Ini: {target_tickers}")
    
    # 2. Persiapan Loop
    target_date = datetime.now().strftime("%Y-%m-%d") # Hari ini
    all_data = []

    # 3. Eksekusi Loop
    for ticker in target_tickers:
        print(f"⏳ Mengambil data {ticker}...", end="")
        
        # Panggil fungsi dari api_client.py
        raw_json = api_client.get_broker_summary(ticker, target_date)
        
        if raw_json == "LIMIT":
            print("⛔ KUOTA HARIAN HABIS! Simpan data yang ada sekarang.")
            break
        
        if raw_json:
            # Panggil fungsi dari data_processor.py
            clean_row = data_processor.parse_bandarmology_json(raw_json, ticker, target_date)
            
            if clean_row:
                all_data.append(clean_row)
                print("✅ OK")
            else:
                print("⚠️ Data Kosong/Libur")
        else:
            print("❌ Error API")
            
        time.sleep(config.DELAY_SECONDS)

    # 4. Simpan Hasil
    if all_data:
        # Pastikan folder data/raw ada
        os.makedirs("data/raw", exist_ok=True)
        
        filename = f"data/raw/harvest_{target_date}.xlsx"
        df = pd.DataFrame(all_data)
        df.to_excel(filename, index=False)
        print(f"\n💾 SUKSES! Data tersimpan di: {filename}")
    else:
        print("\n⚠️ Tidak ada data yang berhasil diambil.")

if __name__ == "__main__":
    run_harvester()