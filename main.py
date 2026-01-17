# main.py
import pandas as pd
import time
from datetime import datetime
import os

# Import modul buatan kita sendiri
import config
from src import api_client, data_processor

# main.py
import pandas as pd
import time
from datetime import datetime, timedelta # Kita pakai timedelta bawaan python saja biar ringan
import os

# Import modul buatan kita sendiri
import config
from src import api_client, data_processor

def run_harvester():
    print("🚀 BANDARMOLOGY TIME MACHINE (PANEN MUNDUR)")
    print("===========================================")
    
    # 1. Target Saham
    target_tickers = getattr(config, 'TARGET_TICKERS', [])
    if not target_tickers: target_tickers = getattr(config, 'WATCHLIST', [])
    
    # 2. KONFIGURASI WAKTU (Ubah ini sesuai kebutuhan)
    # Kita akan mengambil data mundur ke belakang
    start_date = datetime.now() 
    days_to_harvest = 6  # Mau ambil berapa hari ke belakang? (Sesuaikan sisa kuota!)
    
    # Hitung total request yang akan terjadi
    total_req = len(target_tickers) * days_to_harvest
    print(f"🎯 Target: {len(target_tickers)} Saham")
    print(f"📅 Durasi: {days_to_harvest} Hari ke belakang")
    print(f"⚠️ Estimasi Kuota Terpakai: {total_req} Hits")
    
    input("Tekan ENTER untuk mulai panen...")

    all_data = []

    # 3. LOOP TANGGAL (Mundur)
    for i in range(days_to_harvest):
        # Hitung tanggal: Hari ini dikurangi i hari
        current_date_obj = start_date - timedelta(days=i)
        
        # Skip Sabtu (5) dan Minggu (6)
        if current_date_obj.weekday() >= 5:
            continue
            
        date_str = current_date_obj.strftime("%Y-%m-%d")
        print(f"\n📆 PROCESSING TANGGAL: {date_str}")
        print("-" * 30)

        # 4. LOOP SAHAM
        for ticker in target_tickers:
            print(f"⏳ {ticker}...", end="")
            
            raw_json = api_client.get_broker_summary(ticker, date_str)
            
            if raw_json == "LIMIT":
                print("⛔ KUOTA HABIS! Berhenti.")
                # Simpan apa yang sudah dapat
                save_data(all_data)
                return

            if raw_json:
                clean_row = data_processor.parse_bandarmology_json(raw_json, ticker, date_str)
                if clean_row:
                    all_data.append(clean_row)
                    print("✅")
                else:
                    print("⚠️ Kosong")
            else:
                print("❌ Error")
            
            # Jeda biar API tidak ngambek
            time.sleep(0.5)

    # 5. Simpan Hasil Akhir
    save_data(all_data)

def save_data(data):
    if data:
        os.makedirs("data/raw", exist_ok=True)
        # Nama file pakai timestamp biar gak ketimpa
        filename = f"data/raw/harvest_batch_{int(time.time())}.xlsx"
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        print(f"\n💾 SUKSES! {len(df)} data tersimpan di: {filename}")
    else:
        print("\n⚠️ Tidak ada data valid yang terkumpul.")

if __name__ == "__main__":
    run_harvester()