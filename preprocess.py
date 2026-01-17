import pandas as pd
import numpy as np
import os
import glob

def load_and_merge_data():
    print("🔄 MEMULAI PROSES ETL (Extract, Transform, Load)...")
    
    # --- 1. LOAD DATA BANDARMOLOGY (Tabel A) ---
    harvest_files = glob.glob("data/raw/harvest_*.xlsx")
    
    if not harvest_files:
        print("❌ Error: Tidak ditemukan file harvest di data/raw/")
        return None

    print(f"📂 Ditemukan {len(harvest_files)} file data bandar.")
    
    df_list = []
    for file in harvest_files:
        try:
            temp_df = pd.read_excel(file)
            df_list.append(temp_df)
        except Exception as e:
            print(f"⚠️ Gagal baca file {file}: {e}")
            
    if not df_list:
        return None

    df_bandar = pd.concat(df_list, ignore_index=True)
    
    # === CLEANING NAMA KOLOM ===
    # Ubah jadi huruf kecil semua biar aman (top1_buy_vol, ticker, date)
    df_bandar.columns = df_bandar.columns.str.strip().str.lower()
    
    # Pastikan format tanggal konsisten
    df_bandar['date'] = pd.to_datetime(df_bandar['date'])
    df_bandar = df_bandar.drop_duplicates(subset=['ticker', 'date'])
    print(f"✅ Data Bandar Terload: {len(df_bandar)} baris.")

    # --- 2. LOAD DATA HARGA (Tabel B) ---
    price_path = "data/raw/historical_prices_OHLC.xlsx"
    if not os.path.exists(price_path):
        print("❌ Error: File historical_prices_OHLC.xlsx tidak ditemukan!")
        return None
        
    df_price = pd.read_excel(price_path)
    df_price.columns = df_price.columns.str.strip().str.lower()
    df_price['date'] = pd.to_datetime(df_price['date'])
    print(f"✅ Data Harga Terload: {len(df_price)} baris.")

    # --- 3. MERGING (INNER JOIN) ---
    print("⏳ Sedang menggabungkan (Merging)...")
    
    # Validasi kolom wajib
    required_cols = ['ticker', 'date', 'top1_buy_vol'] # Cek sampel satu kolom
    if not all(col in df_bandar.columns for col in required_cols):
        print(f"❌ Error Kolom: Kode mengharapkan {required_cols}")
        print(f"   Tapi yang ditemukan: {list(df_bandar.columns)}")
        return None

    merged_df = pd.merge(
        df_bandar, 
        df_price[['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']], 
        on=['ticker', 'date'], 
        how='inner'
    )
    
    print(f"🤝 Hasil Merging: {len(merged_df)} baris data valid (Sinkron).")
    return merged_df

def create_features(df):
    print("🧪 MEMBUAT FITUR BANDARMOLOGY 3.0 (SMART MONEY FLOW)...")
    
    # Fill NA & Handle Zero Volume
    df['top1_buy_vol'] = df['top1_buy_vol'].fillna(0)
    df['top1_sell_vol'] = df['top1_sell_vol'].fillna(0)
    df['volume'] = df['volume'].replace(0, 1)
    
    # === A. KATEGORI BROKER ===
    retail_brokers = ['YP', 'PD', 'XC', 'KK', 'NI', 'CC', 'XL', 'DR', 'SQ', 'AZ']
    market_maker = ['MG']
    
    df['code_buyer_retail'] = df['top1_buyer'].apply(lambda x: 1 if x in retail_brokers else 0)
    df['code_seller_retail'] = df['top1_seller'].apply(lambda x: 1 if x in retail_brokers else 0)
    
    # === B. FITUR UTAMA ===

    # 1. SMART ACCUMULATION
    df['smart_accumulation'] = (1 - df['code_buyer_retail']) * df['code_seller_retail']

    # 2. DOMINASI BANDAR
    df['buyer_dominance'] = df['top1_buy_vol'] / df['volume']
    df['smart_accumulation_score'] = df['smart_accumulation'] * df['buyer_dominance']
    
    # 3. RETAIL DISGUISE SCORE
    df['retail_disguise_score'] = df['code_buyer_retail'] * df['buyer_dominance']
    
    # 4. PANIC SELLING RITEL
    df['seller_dominance'] = df['top1_sell_vol'] / df['volume']
    
    # 5. NET VOLUME MURNI (INI YANG TADI HILANG) <--- FIX DISINI
    # Kita butuh ini untuk preview dan fitur dasar
    df['net_top1'] = df['top1_buy_vol'] - df['top1_sell_vol']

    # 6. BERSIH KOTOR (Net Buy Ratio)
    total_action_vol = df['top1_buy_vol'] + df['top1_sell_vol'] + 1
    df['net_buy_ratio'] = (df['top1_buy_vol'] - df['top1_sell_vol']) / total_action_vol
    
    # 7. AGGRESSIVENESS (HAKA)
    df['buyer_aggression'] = df['top1_buy_avg'] / (df['close'] + 0.1)
    
    # 8. PANIC ABSORPTION (Nampung ARB)
    df['price_drop_depth'] = (df['close'] - df['open']) / df['open']
    df['panic_absorption_score'] = df['smart_accumulation'] * (df['price_drop_depth'] * -1)
    df['panic_absorption_score'] = df['panic_absorption_score'].apply(lambda x: x if x > 0 else 0)

    # === C. TARGET VARIABLE ===
    print("🎯 MEMBUAT TARGET VARIABLE...")
    df = df.sort_values(by=['ticker', 'date'])
    df['next_close'] = df.groupby('ticker')['close'].shift(-1)
    
    df['target_class'] = np.where(df['next_close'] > df['close'] * 1.005, 1, 0)
    
    df_clean = df.dropna(subset=['next_close'])
    
    return df_clean

def run_pipeline():
    df = load_and_merge_data()
    
    if df is not None:
        final_df = create_features(df)
        
        os.makedirs("data/processed", exist_ok=True)
        output_path = "data/processed/final_dataset.csv"
        final_df.to_csv(output_path, index=False)
        
        print("\n" + "="*40)
        print(f"🚀 SUCCESS! Dataset siap training.")
        print(f"📂 Lokasi: {output_path}")
        print(f"📊 Total Data Training: {len(final_df)} baris")
        print("="*40)
        
        # Cek kolom hasil
        preview_cols = ['date', 'ticker', 'top1_buyer', 'net_top1', 'target_class']
        print(final_df[preview_cols].tail())

if __name__ == "__main__":
    run_pipeline()