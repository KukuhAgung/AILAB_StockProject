import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src import api_client, data_processor

COLLECTED_DIR = "data/collected"
FILE_INVENTORY = os.path.join(COLLECTED_DIR, "inventory_collected.xlsx")
FILE_SHAREHOLDER = os.path.join(COLLECTED_DIR, "shareholder_collected.xlsx")
FILE_FOREIGN = os.path.join(COLLECTED_DIR, "foreign_collected.xlsx") 
_MARKET_SENTIMENT_CACHE = None

def format_big_number(num):
    if abs(num) >= 1e9:
        return f"{num/1e9:.2f} miliar"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.2f} juta"
    else:
        return f"{num:,.0f}"

def _save_collected_data(ticker, df_price, df_sh, comp_data, foreign_data, broker_data):
    """Menyimpan data ke koleksi lokal dengan standarisasi kolom."""
    if not os.path.exists(COLLECTED_DIR):
        os.makedirs(COLLECTED_DIR)
    
    # --- Inventory ---
    df_save = df_price.copy()
    df_save['ticker'] = ticker
    if os.path.exists(FILE_INVENTORY):
        existing = pd.read_excel(FILE_INVENTORY)
        combined = pd.concat([existing, df_save]).drop_duplicates(subset=['ticker', 'date'], keep='last')
        combined.to_excel(FILE_INVENTORY, index=False)
    else:
        df_save.to_excel(FILE_INVENTORY, index=False)
    
    # --- Shareholder History ---
    if not df_sh.empty:
        df_save_sh = df_sh.copy()
        df_save_sh['ticker'] = ticker
        if os.path.exists(FILE_SHAREHOLDER):
            existing = pd.read_excel(FILE_SHAREHOLDER)
            combined = pd.concat([existing, df_save_sh]).drop_duplicates(subset=['ticker', 'date'], keep='last')
            combined.to_excel(FILE_SHAREHOLDER, index=False)
        else:
            df_save_sh.to_excel(FILE_SHAREHOLDER, index=False)
    
    # --- Foreign Snapshot (update per ticker) ---
    # Gabungkan data snapshot menjadi satu baris
    snapshot = {
        'ticker': ticker,
        'top_buyer_code': broker_data.get('top_buyer_code', 'UNKNOWN'),
        'top_buyer_avg': broker_data.get('top_buyer_avg', 0),
        'foreign_net_vol': foreign_data.get('foreign_net_vol', 0),
        'foreign_pct': foreign_data.get('foreign_pct', 0),
        'public_pct': comp_data.get('public_pct', 0),
        'controller_pct': comp_data.get('controller_pct', 0)
    }
    df_snapshot = pd.DataFrame([snapshot])
    
    if os.path.exists(FILE_FOREIGN):
        existing_foreign = pd.read_excel(FILE_FOREIGN)
        # Hapus data lama untuk ticker ini, lalu append yang baru
        existing_foreign = existing_foreign[existing_foreign['ticker'] != ticker]
        combined_foreign = pd.concat([existing_foreign, df_snapshot], ignore_index=True)
        combined_foreign.to_excel(FILE_FOREIGN, index=False)
    else:
        df_snapshot.to_excel(FILE_FOREIGN, index=False)

def get_latest_market_sentiment(force_refresh=False):
    """
    Menghitung market sentiment dari seluruh saham di inventory_collected.xlsx.
    Hasil di-cache untuk efisiensi.
    """
    global _MARKET_SENTIMENT_CACHE
    if _MARKET_SENTIMENT_CACHE is not None and not force_refresh:
        return _MARKET_SENTIMENT_CACHE
    
    if not os.path.exists(FILE_INVENTORY):
        print("⚠️ File inventory_collected.xlsx tidak ditemukan, market sentiment = 0")
        _MARKET_SENTIMENT_CACHE = (0.0, 0.0)
        return _MARKET_SENTIMENT_CACHE
    
    df_inv = pd.read_excel(FILE_INVENTORY)
    df_inv['date'] = pd.to_datetime(df_inv['date'])
    df_inv = df_inv.sort_values('date')
    
    unique_stocks = df_inv['ticker'].nunique()
    if unique_stocks < 10:
        print(f"⚠️ Peringatan: Market sentiment hanya berdasarkan {unique_stocks} saham. Proxy mungkin bias.")
    
    market = df_inv.groupby('date').agg({
        'net_vol': 'sum',
        'volume': 'sum'
    }).reset_index()
    market['market_net_ratio'] = market['net_vol'] / (market['volume'] + 1e-5)
    market['market_ma5'] = market['market_net_ratio'].rolling(5, min_periods=1).mean()
    
    latest = market.iloc[-1]
    _MARKET_SENTIMENT_CACHE = (latest['market_net_ratio'], latest['market_ma5'])
    return _MARKET_SENTIMENT_CACHE

def get_live_data(ticker):
    print(f"📡 Mengambil data live untuk {ticker}...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=300)
    s_str = start_date.strftime("%Y-%m-%d")
    e_str = end_date.strftime("%Y-%m-%d")
    
    try:
        # --- Inventory (Harian) ---
        raw_inv = api_client.get_inventory_chart(ticker, s_str, e_str)
        if not raw_inv:
            print("❌ Data inventory kosong.")
            return None
        
        # --- Broker Snapshot (untuk display) ---
        raw_broker = api_client.get_broker_summary(ticker, s_str, e_str)
        
        # --- Foreign Flow Snapshot ---
        raw_foreign = None
        if hasattr(api_client, 'get_summary_chart'):
            raw_foreign = api_client.get_summary_chart(ticker, s_str, e_str)
        
        # --- Composition Snapshot (FREE FLOAT & CONTROLLER) ---
        raw_comp = None
        if hasattr(api_client, 'get_shareholder_composition'):
            raw_comp = api_client.get_shareholder_composition(ticker)
        
        # --- Shareholder History (opsional, untuk tren) ---
        raw_sh = api_client.get_shareholder_number(ticker)
        
    except Exception as e:
        print(f"⚠️ Error API: {e}")
        return None
    
    # --- 1. Parsing Inventory ---
    df_price = pd.DataFrame(data_processor.parse_price(raw_inv, ticker))
    if df_price.empty:
        return None
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_price = df_price.sort_values('date')
    
    # --- 2. Parsing Snapshot Data ---
    broker_data = data_processor.parse_broker_snapshot(raw_broker, ticker) if raw_broker else {}
    top_buyer_code = broker_data.get('top_buyer_code', 'UNKNOWN')
    top_buyer_avg = broker_data.get('top_buyer_avg', 0)
    
    # Foreign Snapshot
    foreign_data = data_processor.parse_foreign_flow(raw_foreign, ticker) if raw_foreign else {}
    foreign_net_vol = foreign_data.get('foreign_net_vol', 0)
    foreign_pct = foreign_data.get('foreign_pct', 0)
    
    # Composition Snapshot (FREE FLOAT & CONTROLLER)
    comp_data = data_processor.parse_composition(raw_comp, ticker) if raw_comp else {}
    public_pct = comp_data.get('public_pct', 0)
    controller_pct = comp_data.get('controller_pct', 0)
    
    # --- 3. Parsing Shareholder History (opsional) ---
    df_sh = pd.DataFrame()
    if raw_sh:
        try:
            df_sh = pd.DataFrame(data_processor.parse_shareholder(raw_sh, ticker))
            if not df_sh.empty:
                df_sh['date'] = pd.to_datetime(df_sh['date'])
                df_sh = df_sh.sort_values('date')
                df_sh = df_sh.rename(columns={'value': 'shareholder_count'})
        except:
            pass
    
    # --- 4. Merge as-of shareholder history (hanya untuk tren) ---
    if not df_sh.empty:
        df = pd.merge_asof(
            df_price.sort_values('date'),
            df_sh[['date', 'shareholder_count']].sort_values('date'),
            on='date',
            direction='backward'
        )
        df['shareholder_count'] = df['shareholder_count'].ffill()
    else:
        df = df_price.copy()
        df['shareholder_count'] = np.nan
    
    # --- 5. Tempelkan snapshot ownership ke setiap baris (konstan) ---
    df['foreign_net_vol'] = foreign_net_vol
    df['foreign_pct'] = foreign_pct
    df['public_pct'] = public_pct
    df['controller_pct'] = controller_pct
    df['top_buyer_code'] = top_buyer_code
    df['top_buyer_avg'] = top_buyer_avg
    
    # --- 6. Simpan ke collected (untuk keperluan training/market sentiment) ---
    _save_collected_data(ticker, df_price, df_sh, comp_data, foreign_data, broker_data)
    
    return df

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window, min_periods=window-5).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window, min_periods=window-5).mean()
    rs = gain / (loss + 1e-5)
    return 100 - (100 / (1 + rs))

def calculate_features(df, market_net_ratio, market_ma5, feature_list):
    """
    Menghitung fitur untuk baris TERAKHIR.
    Semua rolling window menggunakan data masa lalu (min_periods).
    """
    df = df.copy()
    df = df.sort_values('date')
    
    # --- 1. Net Volume ---
    df['net_vol_5d_sum'] = df['net_vol'].rolling(5, min_periods=3).sum()
    df['net_vol_20d_sum'] = df['net_vol'].rolling(20, min_periods=10).sum()
    
    # --- 2. RSI ---
    df['rsi_14'] = calculate_rsi(df['close'])
    
    # --- 3. ATR ---
    df['high_low_pct'] = (df['high'] - df['low']) / df['close']
    df['atr_10d'] = df['high_low_pct'].rolling(10, min_periods=5).mean()
    
    # --- 4. VWAP 20 (proxy bandar) ---
    df['vol_price'] = df['close'] * df['volume']
    df['rolling_vol_price'] = df['vol_price'].rolling(20, min_periods=5).sum()
    df['rolling_vol'] = df['volume'].rolling(20, min_periods=5).sum()
    df['vwap_20'] = df['rolling_vol_price'] / (df['rolling_vol'] + 1e-5)
    df['price_vs_vwap'] = (df['close'] - df['vwap_20']) / (df['vwap_20'] + 1e-5)
    
    # --- 5. Moving Average & Trend ---
    df['ma_20'] = df['close'].rolling(20, min_periods=5).mean()
    df['ma_50'] = df['close'].rolling(50, min_periods=10).mean()
    df['price_vs_ma20'] = (df['close'] - df['ma_20']) / (df['ma_20'] + 1e-5)
    df['trend_strong'] = np.where(df['ma_20'] > df['ma_50'], 1, 0)
    
    # --- 6. Interaksi ---
    df['interaction_vol_atr'] = df['net_vol_5d_sum'] * df['atr_10d']
    
    # --- 7. Fitur Struktur Kepemilikan (dari snapshot) ---
    df['is_foreign_stock'] = np.where(df['foreign_pct'] > 0.2, 1, 0)
    df['float_risk'] = np.where((df['public_pct'] < 0.05) | (df['public_pct'] > 0.80), 1, 0)
    df['strong_controller'] = np.where(df['controller_pct'] > 0.5, 1, 0)
    
    # --- 8. Market Context ---
    df['market_net_ratio'] = market_net_ratio
    df['market_ma5'] = market_ma5
    
    # --- Sinyal tambahan untuk analisis (bukan fitur model) ---
    df['accum_signal'] = ((df['close'].pct_change(5) < 0.01) & 
                          (df['net_vol_5d_sum'] > 0) & 
                          (df['price_vs_vwap'] < 0)).astype(int)
    
    # --- 9. Shareholder Change (jika ada) ---
    if 'shareholder_count' in df.columns:
        df['sh_change_mom'] = df['shareholder_count'].pct_change(20)
        df['is_retail_panic'] = np.where((df['sh_change_mom'] < -0.01) & (df['close'] < df['ma_20']), 1, 0)
    else:
        df['sh_change_mom'] = 0
        df['is_retail_panic'] = 0
    
    # --- Ambil baris terakhir ---
    latest = df.iloc[[-1]].copy()
    
    # --- Tambahkan metrik analisis tambahan untuk Gemini ---
    if len(df) >= 6:
        price_5d_ago = df['close'].iloc[-6]
        latest['price_change_5d'] = (latest['close'].values[0] - price_5d_ago) / price_5d_ago
    else:
        latest['price_change_5d'] = 0.0
    
    avg_vol_20 = df['volume'].rolling(20, min_periods=5).mean().iloc[-1]
    latest['avg_volume_20'] = avg_vol_20
    latest['volume_ratio'] = latest['volume'].values[0] / avg_vol_20 if avg_vol_20 > 0 else 1.0
    
    # --- Rentang intraday dalam persen ---
    latest['intraday_range_pct'] = (latest['high'].values[0] - latest['low'].values[0]) / latest['close'].values[0]
    
    for col in feature_list:
        if col not in latest.columns:
            if col in df.columns:
                latest[col] = df[col].iloc[-1]
            else:
                latest[col] = 0
    
    latest = latest.fillna(0)
    
    return latest