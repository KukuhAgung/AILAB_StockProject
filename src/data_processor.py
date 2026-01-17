import pandas as pd

def parse_inventory_timeseries(json_data, ticker):
    """
    Mengubah JSON Inventory Chart (Nested) menjadi Flat List Harian.
    Menghitung Total Net Volume dari Top Broker yang tersedia di chart.
    """
    try:
        if not json_data or 'price' not in json_data:
            return []

        # 1. Agregasi Net Volume Bandar per Tanggal
        # Format map: {'2026-01-02': 50000, '2026-01-03': -20000, ...}
        whale_net_vol_map = {}
        
        if 'broker' in json_data:
            for broker_item in json_data['broker']:
                # Loop data harian setiap broker (MG, YP, dll)
                for daily_item in broker_item.get('data', []):
                    # Ambil tanggal saja (YYYY-MM-DD)
                    d_date = daily_item['date'].split("T")[0] 
                    val = daily_item.get('value', 0) # Value ini adalah VOLUME (Lot) karena scope='vol'
                    
                    if d_date not in whale_net_vol_map:
                        whale_net_vol_map[d_date] = 0
                    
                    # Jumlahkan akumulasi semua top broker hari itu
                    whale_net_vol_map[d_date] += val

        # 2. Gabungkan dengan Data OHLC Price
        parsed_rows = []
        for p in json_data['price']:
            d_date = p['date'].split("T")[0]
            
            # Ambil net volume bandar di tanggal yang sama (default 0 jika tidak ada data)
            net_vol = whale_net_vol_map.get(d_date, 0)
            
            row = {
                'ticker': ticker,
                'date': d_date,
                'open': p.get('open'),
                'high': p.get('high'),
                'low': p.get('low'),
                'close': p.get('close'),
                'volume': p.get('volume'),
                'net_vol': net_vol
            }
            parsed_rows.append(row)
            
        return parsed_rows

    except Exception as e:
        print(f"⚠️ Error parsing inventory for {ticker}: {e}")
        return []

def parse_broker_snapshot(json_data, ticker):
    """
    Mengambil Top 1 Buyer dari Broker Summary sebagai referensi statis/snapshot.
    """
    try:
        if not json_data: return None
        
        # Urutkan berdasarkan Net Volume Terbesar (Accumulation)
        sorted_brokers = sorted(json_data, key=lambda x: (int(x['buy_volume']) - int(x['sell_volume'])), reverse=True)
        
        top_buyer = sorted_brokers[0]
        net_vol = int(top_buyer['buy_volume']) - int(top_buyer['sell_volume'])
        
        return {
            'ticker': ticker,
            'top_buyer_code': top_buyer['code'],
            'top_buyer_avg': float(top_buyer['buy_avg']),
            'total_net_vol_300d': net_vol
        }
    except Exception:
        return None

def parse_invezgo_shareholder(json_data, ticker):
    try:
        rows = []
        for item in json_data:
            rows.append({
                'ticker': ticker,
                'date': item['date'].split("T")[0], # Ambil tanggal
                'value': item['value'] # Jumlah pemegang saham
            })
        return rows
    except Exception:
        return []