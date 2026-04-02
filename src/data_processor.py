import pandas as pd
import numpy as np

def parse_price(json_data, ticker):
    """
    [DULUNYA: parse__inventory_timeseries]
    Mengubah JSON Inventory Chart (Nested) menjadi Flat List Harian.
    Menghitung Total Net Volume dari Top Broker yang tersedia di chart.
    """
    try:
        if not json_data or 'price' not in json_data:
            return []

        # 1. Agregasi Net Volume Bandar per Tanggal
        whale_net_vol_map = {}
        
        if 'broker' in json_data:
            for broker_item in json_data['broker']:
                # Loop data harian setiap broker (MG, YP, dll)
                for daily_item in broker_item.get('data', []):
                    d_date = daily_item['date'].split("T")[0] 
                    val = daily_item.get('value', 0) 
                    
                    if d_date not in whale_net_vol_map:
                        whale_net_vol_map[d_date] = 0
                    
                    # Jumlahkan akumulasi semua top broker hari itu
                    whale_net_vol_map[d_date] += val

        # 2. Gabungkan dengan Data OHLC Price
        parse_d_rows = []
        for p in json_data['price']:
            d_date = p['date'].split("T")[0]
            
            # Ambil net volume bandar di tanggal yang sama (default 0 jika tidak ada data)
            net_vol = whale_net_vol_map.get(d_date, 0)
            
            row = {
                'ticker': ticker,
                'date': d_date,
                'open': float(p.get('open', 0)),
                'high': float(p.get('high', 0)),
                'low': float(p.get('low', 0)),
                'close': float(p.get('close', 0)),
                'volume': float(p.get('volume', 0)),
                'net_vol': float(net_vol)
            }
            parse_d_rows.append(row)
            
        return parse_d_rows

    except Exception as e:
        print(f"⚠️ Error parsing inventory for {ticker}: {e}")
        return []

def parse_broker_snapshot(raw_data, ticker):
    """
    Menganalisa Broker Summary dengan Filter ANTI-RITEL.
    Hanya mengambil Top Buyer dari broker Institusi/Bandar, mengabaikan broker ritel.
    
    [UPDATE LOGIC]
    Menghitung Manual Average Price = Buy Value / Buy Volume agar akurat sesuai Stockbit.
    """
    default_res = {'top_buyer_code': 'CC', 'top_buyer_avg': 0}

    # DAFTAR BLACKLIST BROKER RITEL
    # XL = Stockbit, YP = Mirae, PD = IPOT, XC = Ajaib, NI = BNI Ritel, KK = Phillips
    RETAIL_BLOCKLIST = ['XL', 'YP', 'PD', 'XC', 'NI', 'KK', 'XQ']

    try:
        if not raw_data: 
            return default_res
        
        # Normalisasi input (handle jika input berupa dict wrapper)
        data_to_sort = raw_data
        if isinstance(raw_data, dict):
            # API kadang mengembalikan list langsung, kadang dict dengan key 'buy'
            data_to_sort = raw_data.get('buy', []) if 'buy' in raw_data else raw_data

        if not isinstance(data_to_sort, list) or not data_to_sort:
            return default_res

        # Urutkan berdasarkan Net Buy Volume Terbesar (Accumulation Power)
        # Rumus: Buy Volume - Sell Volume
        sorted_brokers = sorted(
            data_to_sort, 
            key=lambda x: (float(x.get('buy_volume', 0)) - float(x.get('sell_volume', 0))), 
            reverse=True
        )
        
        # --- LOGIKA PENCARIAN BANDAR (NON-RITEL) ---
        selected_broker = None
        
        for broker in sorted_brokers:
            code = broker.get('code') or broker.get('broker_code')
            
            # Jika broker ini ada di BLACKLIST RITEL, skip!
            if code in RETAIL_BLOCKLIST:
                continue
            
            # Jika bukan ritel, ambil ini sebagai Bandar Utama
            selected_broker = broker
            break
        
        # Fallback: Jika isinya ritel semua (jarang terjadi), terpaksa ambil Top 1
        if selected_broker is None and sorted_brokers:
            selected_broker = sorted_brokers[0]

        if not selected_broker:
            return default_res

        # --- UPDATE PENTING: KALKULASI MANUAL AVG PRICE ---
        # Jangan gunakan field 'buy_avg' dari API karena sering tidak akurat (kasus DEWA/MLPL).
        # Gunakan rumus: Total Buy Value / Total Buy Volume
        
        buy_val = float(selected_broker.get('buy_value', 0))
        buy_vol = float(selected_broker.get('buy_volume', 0))
        
        if buy_vol > 0:
            manual_avg = buy_val / buy_vol # Ini akan match dengan Stockbit (misal: 553 untuk DEWA)
        else:
            manual_avg = float(selected_broker.get('buy_avg') or 0) # Fallback

        code = selected_broker.get('code') or selected_broker.get('broker_code')

        return {
            'ticker': ticker,
            'top_buyer_code': code,
            'top_buyer_avg': manual_avg # Simpan hasil hitungan manual
        }

    except Exception as e:
        print(f"⚠️ Error parsing broker snapshot: {e}")
        return default_res

def parse_shareholder(json_data, ticker):
    """
    Mengambil data jumlah pemegang saham.
    """
    try:
        if not json_data: return []

        rows = []
        for item in json_data:
            rows.append({
                'ticker': ticker,
                'date': item['date'].split("T")[0], 
                'value': float(item.get('value', 0) or item.get('total_shareholder', 0))
            })
        return rows
    except Exception:
        return []
    

def parse_foreign_flow(json_data, ticker):
    """
    Mengambil data Net Buy Asing vs Domestik.
    """
    try:
        if not json_data: return None
        
        f_buy, f_sell, d_buy, d_sell = 0, 0, 0, 0
        
        for item in json_data:
            lbl = item.get('label', '')
            val = float(item.get('value', 0))
            if lbl == 'F Buy': f_buy = val
            elif lbl == 'F Sell': f_sell = val
            elif lbl == 'D Buy': d_buy = val
            elif lbl == 'D Sell': d_sell = val
            
        total_vol = f_buy + f_sell + d_buy + d_sell
        
        return {
            'ticker': ticker,
            'foreign_net_vol': f_buy - f_sell,
            'foreign_pct': ((f_buy + f_sell) / total_vol) if total_vol > 0 else 0 
        }
    except Exception:
        return None


def parse_composition(json_data, ticker):
    """
    Mengambil Persentase Masyarakat & Pengendali.
    """
    try:
        if not json_data: return None
        
        public_pct = 0
        controller_pct = 0
        
        for item in json_data:
            name = item.get('name', '').lower()
            badge = item.get('badge', '')
            pct = float(item.get('percentage', 0))
            
            if 'masyarakat' in name and pct > 0 or 'public' in name:
                public_pct += pct
            
            if 'PENGENDALI' in badge:
                controller_pct += pct
                
        return {
            'ticker': ticker,
            'public_pct': public_pct / 100,
            'controller_pct': controller_pct / 100
        }
    except Exception:
        return None