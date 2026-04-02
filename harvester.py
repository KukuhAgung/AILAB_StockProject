import pandas as pd
import time
from datetime import datetime, timedelta
import os
import config
from src import api_client, data_processor

def run_ultimate_harvester():
    print("🌟 ULTIMATE HARVESTER: 3 PILLARS (Broker + Foreign + Composition)")
    print("=================================================================")
    
    # 1. Setup Target & Waktu
    target_tickers = getattr(config, 'TARGET_TICKERS', [])
    if not target_tickers: target_tickers = getattr(config, 'WATCHLIST', [])
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90) # 300 Hari ke belakang
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    # Estimasi Kuota: 3 Request x Jumlah Saham
    est_quota = len(target_tickers) * 3
    print(f"🎯 Target: {len(target_tickers)} Saham")
    print(f"📊 Estimasi Kuota: ~{est_quota} Hits (Sangat Aman)")
    
    input("👉 Tekan ENTER untuk mulai panen data...")
    
    # Penampung Data Terpisah (Agar mudah di-merge nanti)
    data_broker = []
    data_foreign = []
    data_comp = []
    
    # 2. Loop Eksekusi
    for i, ticker in enumerate(target_tickers):
        print(f"[{i+1}/{len(target_tickers)}] {ticker}...", end=" ")
        
        try:
            # --- API 1: BROKER SUMMARY (The Anchor) ---
            raw_bro = api_client.get_broker_summary(ticker, start_str, end_str)
            if raw_bro and raw_bro != "LIMIT":
                p_bro = data_processor.parse_broker_snapshot(raw_bro, ticker)
                if p_bro: data_broker.append(p_bro)
            
            # --- API 2: FOREIGN FLOW (New Feature) ---
            # Pastikan fungsi get_summary_chart ada di api_client.py
            if hasattr(api_client, 'get_summary_chart'):
                raw_chart = api_client.get_summary_chart(ticker, start_str, end_str)
                p_for = data_processor.parse_foreign_flow(raw_chart, ticker)
                if p_for: data_foreign.append(p_for)

            # --- API 3: SHAREHOLDER COMPOSITION (New Feature) ---
            # Pastikan fungsi get_shareholder_composition ada di api_client.py
            if hasattr(api_client, 'get_shareholder_composition'):
                raw_comp = api_client.get_shareholder_composition(ticker)
                p_comp = data_processor.parse_composition(raw_comp, ticker)
                if p_comp: data_comp.append(p_comp)

            print("✅")
            time.sleep(0.2) # Jeda aman (5 req/detik)

        except Exception as e:
            print(f"❌ {e}")
            continue

    # 3. Penggabungan Data (Merging)
    print("\n🔄 Menggabungkan Data...")
    
    if not data_broker:
        print("❌ Gagal: Tidak ada data broker yang terambil.")
        return

    # Convert ke DataFrame
    df_main = pd.DataFrame(data_broker)
    df_foreign = pd.DataFrame(data_foreign)
    df_comp = pd.DataFrame(data_comp)
    
    # Left Join: Menggabungkan Foreign & Comp ke tabel Broker berdasarkan 'ticker'
    if not df_foreign.empty:
        df_main = pd.merge(df_main, df_foreign, on='ticker', how='left')
    
    if not df_comp.empty:
        df_main = pd.merge(df_main, df_comp, on='ticker', how='left')
    
    # 4. Simpan File Final
    os.makedirs("data/raw", exist_ok=True)
    ts = int(time.time())
    filename = f"data/raw/90d/foreign_{ts}.xlsx"
    
    df_main.to_excel(filename, index=False)
    
    print("="*50)
    print(f"🏆 SELESAI! Dataset Ultimate Tersimpan.")
    print(f"📂 Lokasi: {filename}")
    print(f"📊 Total Baris: {len(df_main)}")
    print("👉 Update path 'PATH_RAW_BROKER' di train.py ke file ini.")
    print("="*50)

if __name__ == "__main__":
    run_ultimate_harvester()