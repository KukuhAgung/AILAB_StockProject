import pandas as pd
import time
from datetime import datetime, timedelta
import os
import streamlit as st
from src import api_client, data_processor

def run_harvester():
    print("🚀 INVEZGO HYBRID HARVESTER (MODE: WHALE TRACKING & RE-CALCULATION)")
    print("==================================================================")
    
    # 1. Load Target
    target_tickers = st.secrets.get("TARGET_TICKERS", [])
    if not target_tickers: target_tickers = st.secrets.get("WATCHLIST", [])
    
    # 2. Setup Waktu
    # Mengambil data 300 hari ke belakang untuk membentuk dataset Raw yang solid
    end_date = datetime.now()
    days_to_harvest = 90  
    start_date = end_date - timedelta(days=days_to_harvest)
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"🎯 Target: {len(target_tickers)} Saham")
    print(f"📅 Periode: {start_str} s/d {end_str}")
    print(f"⚠️ Mode: scope='vol' (Satuan Lot)")
    
    input("Tekan ENTER untuk mulai panen data (Re-Scraping)...")

    all_broker_summary = [] 
    all_inventory_ts = []   
    all_shareholder_data = []
    
    stop_signal = False # Flag untuk berhenti darurat

    # 3. Loop Eksekusi
    for i, ticker in enumerate(target_tickers):
        print(f"[{i+1}/{len(target_tickers)}] {ticker}...", end=" ")

        # --- A. Broker Snapshot (UPDATED LOGIC: MANUAL CALC) ---
        # Mengambil raw data broker summary
        raw_broker = api_client.get_broker_summary(ticker, start_str, end_str)
        
        # [CEK 401]
        if raw_broker == "UNAUTHORIZED":
            print("\n⛔ CRITICAL ERROR: TOKEN EXPIRED (401). Stopping Process...")
            stop_signal = True
            break
        elif raw_broker == "LIMIT":
            print("\n⛔ LIMIT REACHED!"); break
            
        if raw_broker and raw_broker != "LIMIT":
            # GUNAKAN FUNGSI BARU: parse_broker_snapshot
            parse_d_broker = data_processor.parse_broker_snapshot(raw_broker, ticker)
            if parse_d_broker: all_broker_summary.append(parse_d_broker)

        # --- B. Inventory Chart / Price (UPDATED NAME) ---
        # Mengambil raw data chart (Open, High, Low, Close, Volume + Net Broker Vol)
        raw_inventory = api_client.get_inventory_chart(ticker, start_str, end_str, scope='vol')
        
        # [CEK 401]
        if raw_inventory == "UNAUTHORIZED":
            print("\n⛔ CRITICAL ERROR: TOKEN EXPIRED (401). Stopping Process...")
            stop_signal = True
            break
            
        if raw_inventory:
            # GUNAKAN FUNGSI BARU: parse_price
            parse_d_ts = data_processor.parse_price(raw_inventory, ticker)
            if parse_d_ts: all_inventory_ts.extend(parse_d_ts)

        # --- C. Shareholder (NAME MATCH) ---
        raw_sh = api_client.get_shareholder_number(ticker)
        
        # [CEK 401]
        if raw_sh == "UNAUTHORIZED":
            print("\n⛔ CRITICAL ERROR: TOKEN EXPIRED (401). Stopping Process...")
            stop_signal = True
            break
            
        if raw_sh:
            parse_d_sh = data_processor.parse_shareholder(raw_sh, ticker)
            if parse_d_sh: all_shareholder_data.extend(parse_d_sh)
        
        print("✅")
        # Beri jeda sedikit agar tidak terkena Rate Limit API
        time.sleep(0.5)

    # 4. Simpan Data
    save_data(all_broker_summary, all_inventory_ts, all_shareholder_data)
    
    if stop_signal:
        print("\n⚠️ PROSES DIHENTIKAN PAKSA KARENA TOKEN INVALID.")
        print("👉 Silakan update token baru di .env atau config, lalu jalankan lagi.")

def save_data(broker, inventory, shareholder):
    os.makedirs("data/raw", exist_ok=True)
    ts = int(time.time())
    
    if inventory:
        pd.DataFrame(inventory).to_excel(f"data/raw/90d/inventory_ts_{ts}.xlsx", index=False)
        print(f"💾 Disimpan: data/raw/90d/inventory_ts_{ts}.xlsx (Data Harga & Volume Harian)")
    
    if broker:
        # File ini sekarang akan berisi 'top_buyer_avg' yang BENAR (Sesuai Stockbit)
        pd.DataFrame(broker).to_excel(f"data/raw/90d/broker_snapshot_{ts}.xlsx", index=False)
        print(f"💾 Disimpan: data/raw/90d/broker_snapshot_{ts}.xlsx (Data Broker Terkoreksi)")
    
    if shareholder:
        pd.DataFrame(shareholder).to_excel(f"data/raw/90d/shareholder_{ts}.xlsx", index=False)
        print(f"💾 Disimpan: data/raw/90d/shareholder_{ts}.xlsx")

if __name__ == "__main__":
    run_harvester()