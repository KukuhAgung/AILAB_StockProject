# predict.py
import pandas as pd
import joblib
import os
from datetime import datetime, timedelta
from src import api_client, data_processor

def get_live_data(ticker):
    print(f"📡 Mengambil data live untuk {ticker}...")
    
    # Invezgo butuh range. Kita ambil 40 hari terakhir untuk memastikan MA20 aman.
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=40)).strftime("%Y-%m-%d")

    # 1. Ambil data gabungan dari Invezgo
    raw_broker = api_client.get_broker_summary(ticker, start_date, end_date)
    raw_inventory = api_client.get_inventory_chart(ticker, start_date, end_date)
    raw_sh = api_client.get_shareholder_number(ticker)

    if not all([raw_broker, raw_inventory, raw_sh]):
        print("❌ Gagal mengambil salah satu komponen data.")
        return None

    # 2. Parsing ke DataFrame
    df_price = pd.DataFrame(data_processor.parse_invezgo_price(raw_inventory, ticker))
    # Untuk prediksi hari ini, kita ambil akumulasi broker summary periode terakhir
    broker_row = data_processor.parse_invezgo_broker(raw_broker, ticker, start_date, end_date)
    df_sh = pd.DataFrame(data_processor.parse_invezgo_shareholder(raw_sh, ticker))

    # 3. Simple Merging untuk Prediksi
    df_price['date'] = pd.to_datetime(df_price['date']).dt.date
    df_sh['date'] = pd.to_datetime(df_sh['date']).dt.date
    
    # Gabungkan harga dengan data shareholder terbaru (ffill)
    df = pd.merge(df_price, df_sh, on=['ticker', 'date'], how='left').sort_values('date')
    df['shareholder_count'] = df['shareholder_count'].ffill()
    
    # Masukkan data broker summary ke baris terakhir
    for key, val in broker_row.items():
        if key not in ['ticker', 'date']:
            df.loc[df.index[-1], key] = val

    return df

def calculate_features(df):
    # Hitung fitur minimal yang dibutuhkan model (harus sama dengan train_model.py)
    df['ma20'] = df['close'].rolling(20).mean()
    df['trend_position'] = df['close'] / df['ma20']
    df['avg_lot_size'] = df['buy_volume'] / (df['buy_freq'] + 1)
    df['rvol'] = df['volume'] / (df['volume'].rolling(20).mean() + 1)
    df['sh_change'] = df['shareholder_count'].diff()
    df['retail_expansion'] = (df['sh_change'] > 0).astype(int)
    df['inventory_velocity'] = df['buy_volume'] - df['sell_volume'] # Sederhana untuk live
    
    return df.iloc[-1:] # Ambil baris terakhir saja untuk prediksi

def run_prediction():
    model_path = "models/final_blend_model.pkl"
    if not os.path.exists(model_path):
        print("❌ Model tidak ditemukan! Jalankan train_model.py dulu.")
        return

    meta = joblib.load(model_path)
    ticker = input("🔍 Masukkan Kode Saham (contoh: BBCA): ").upper()
    
    df_live = get_live_data(ticker)
    if df_live is None: return

    df_feat = calculate_features(df_live)
    X = df_feat[meta['features']].values

    # Prediksi Blending
    p_lgb = meta['lgb_model'].predict(X)[0]
    p_rf = meta['rf_model'].predict_proba(X)[0, 1]
    
    final_prob = (meta['config']['w_lgb'] * p_lgb) + (meta['config']['w_rf'] * p_rf)
    threshold = meta['config']['thr']

    print(f"\n📊 HASIL ANALISIS AI UNTUK {ticker}")
    print(f"------------------------------------")
    print(f"📈 Probabilitas Naik: {final_prob:.2%}")
    print(f"📉 Threshold Model  : {threshold:.2%}")
    
    # Logika Keputusan Berdasarkan Preferensi User
    trend = df_feat['trend_position'].values[0]
    
    if final_prob >= threshold:
        if trend > 1.01:
            print("🔥 SIGNAL: [ BUY ] - Konfirmasi Markup & Akumulasi Kuat.")
        elif trend < 1.0:
            print("⚠️ SIGNAL: [ WAIT ] - Akumulasi Terdeteksi, Tapi Masih Fase Awal (Downtrend).")
        else:
            print("✅ SIGNAL: [ SPECULATIVE BUY ] - Transisi Menuju Uptrend.")
    else:
        print("❌ SIGNAL: [ AVOID ] - Belum Ada Sinyal Akumulasi Signifikan.")

if __name__ == "__main__":
    run_prediction()