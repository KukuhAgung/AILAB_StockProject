import pandas as pd
import time
from datetime import datetime, timedelta
import os
import config
from src import api_client, data_processor

def run_harvester():
    print("🚀 INVEZGO HYBRID HARVESTER (MODE: WHALE TRACKING)")
    print("==================================================")
    
    # 1. Load Target
    target_tickers = getattr(config, 'TARGET_TICKERS', [])
    if not target_tickers: target_tickers = getattr(config, 'WATCHLIST', [])
    
    # 2. Setup Waktu (300 Hari ke Belakang)
    end_date = datetime.now()
    days_to_harvest = 300  
    start_date = end_date - timedelta(days=days_to_harvest)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"🎯 Target: {len(target_tickers)} Saham")
    print(f"📅 Periode: {start_str} s/d {end_str}")
    print(f"⚠️ Mode: scope='vol' (Satuan Lot)")
    
    input("Tekan ENTER untuk mulai panen data...")

    all_broker_summary = [] 
    all_inventory_ts = []   
    all_shareholder_data = []
    
    stop_signal = False # Flag untuk berhenti darurat

    # 3. Loop Eksekusi
    for i, ticker in enumerate(target_tickers):
        print(f"[{i+1}/{len(target_tickers)}] {ticker}...", end=" ")

        # --- A. Broker Snapshot ---
        raw_broker = api_client.get_broker_summary(ticker, start_str, end_str)
        
        # [CEK 401]
        if raw_broker == "UNAUTHORIZED":
            print("\n⛔ CRITICAL ERROR: TOKEN EXPIRED (401). Stopping Process...")
            stop_signal = True
            break # Keluar dari loop
        elif raw_broker == "LIMIT":
            print("\n⛔ LIMIT REACHED!"); break
            
        if raw_broker and raw_broker != "LIMIT":
            parsed_broker = data_processor.parse_broker_snapshot(raw_broker, ticker)
            if parsed_broker: all_broker_summary.append(parsed_broker)

        # --- B. Inventory Chart (Time Series) ---
        raw_inventory = api_client.get_inventory_chart(ticker, start_str, end_str, scope='vol')
        
        # [CEK 401]
        if raw_inventory == "UNAUTHORIZED":
            print("\n⛔ CRITICAL ERROR: TOKEN EXPIRED (401). Stopping Process...")
            stop_signal = True
            break
            
        if raw_inventory:
            parsed_ts = data_processor.parse_inventory_timeseries(raw_inventory, ticker)
            if parsed_ts: all_inventory_ts.extend(parsed_ts)

        # --- C. Shareholder ---
        raw_sh = api_client.get_shareholder_number(ticker)
        
        # [CEK 401]
        if raw_sh == "UNAUTHORIZED":
            print("\n⛔ CRITICAL ERROR: TOKEN EXPIRED (401). Stopping Process...")
            stop_signal = True
            break
            
        if raw_sh:
            parsed_sh = data_processor.parse_invezgo_shareholder(raw_sh, ticker)
            if parsed_sh: all_shareholder_data.extend(parsed_sh)
        
        print("✅")
        time.sleep(0.5)

    # 4. Simpan Data (Meskipun berhenti di tengah jalan, simpan yang sudah dapat)
    save_data(all_broker_summary, all_inventory_ts, all_shareholder_data)
    
    if stop_signal:
        print("\n⚠️ PROSES DIHENTIKAN PAKSA KARENA TOKEN INVALID.")
        print("👉 Silakan update token baru di .env atau config, lalu jalankan lagi.")

def save_data(broker, inventory, shareholder):
    os.makedirs("data/raw", exist_ok=True)
    ts = int(time.time())
    
    if inventory:
        pd.DataFrame(inventory).to_excel(f"data/raw/inventory_ts_{ts}.xlsx", index=False)
        print(f"💾 Disimpan: data/raw/inventory_ts_{ts}.xlsx (Data Utama)")
    
    if broker:
        pd.DataFrame(broker).to_excel(f"data/raw/broker_snapshot_{ts}.xlsx", index=False)
    
    if shareholder:
        pd.DataFrame(shareholder).to_excel(f"data/raw/shareholder_{ts}.xlsx", index=False)

if __name__ == "__main__":
    run_harvester()