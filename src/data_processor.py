# src/data_processor.py

def parse_bandarmology_json(data, ticker, date_str):
    """Memproses JSON mentah menjadi baris data siap Excel."""
    
    # Validasi data kosong
    if not data or 'data' not in data or 'results' not in data['data']:
        return None
    
    transactions = data['data']['results']
    if not transactions:
        return None

    # Logika Sorting Buyer & Seller
    buyers = sorted([t for t in transactions if t['side'] == 'BUY'], key=lambda x: x['lot'], reverse=True)
    sellers = sorted([t for t in transactions if t['side'] == 'SELL'], key=lambda x: x['lot'], reverse=True)

    # Handle jika list kosong (Safeguard)
    top1_buy = buyers[0] if buyers else {'broker': {'code': 'None'}, 'lot': 0, 'avg': 0}
    top1_sell = sellers[0] if sellers else {'broker': {'code': 'None'}, 'lot': 0, 'avg': 0}
    
    # Return dictionary bersih
    return {
        'date': date_str,
        'ticker': ticker,
        'top1_buyer': top1_buy['broker']['code'],
        'top1_buy_vol': top1_buy['lot'],
        'top1_buy_avg': top1_buy['avg'],
        'top1_seller': top1_sell['broker']['code'],
        'top1_sell_vol': top1_sell['lot'],
        'top1_sell_avg': top1_sell['avg']
    }