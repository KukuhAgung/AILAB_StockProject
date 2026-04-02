import streamlit as st
import joblib
import os
from datetime import datetime
from google import genai
from google.genai import types
import plotly.graph_objects as go

from src import helper

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Warning: Gagal inisialisasi Gemini. {e}")
    client = None

def get_gemini_advice(ticker, price, profile, tech_data, market_data, prob, threshold, reasons):
    """
    Menghasilkan narasi analisis mendalam menggunakan Gemini.
    """
    if not client:
        return "Gemini Client tidak tersedia."

    dist_vwap = tech_data.get('dist_to_vwap', 0)
    bandar_status = "DISKON (harga di bawah VWAP)" if dist_vwap < 0 else "PREMIUM (harga di atas VWAP)"
    
    net_vol_status = "AKUMULASI" if tech_data.get('net_vol_5d_sum', 0) > 0 else "DISTRIBUSI"
    rsi_status = "OVERSOLD" if tech_data.get('rsi_14', 50) < 30 else "OVERBOUGHT" if tech_data.get('rsi_14', 50) > 70 else "NETRAL"
    
    public_pct = profile.get('public_pct', 0)
    if public_pct < 0.05:
        likuiditas_risk = "SANGAT RENDAH – rawan gorengan, sulit exit"
    elif public_pct > 0.8:
        likuiditas_risk = "SANGAT TINGGI – banyak ritel, potensi panic selling"
    else:
        likuiditas_risk = "✅ NORMAL – likuiditas mencukupi"
    
    foreign_pct = profile.get('foreign_pct', 0)
    asing_desc = "DOMINAN – pergerakan harga dipengaruhi asing" if foreign_pct > 0.3 else "MINOR – pergerakan lebih dipengaruhi lokal"

    price_change_5d = tech_data.get('price_change_5d', 0)
    open_price = tech_data.get('open', price)
    high_price = tech_data.get('high', price)
    low_price = tech_data.get('low', price)
    volume_ratio = tech_data.get('volume_ratio', 1.0)
    
    sys_instruct = """
    Anda adalah Senior Equity Analyst independen di perusahaan sekuritas terkemuka Indonesia, spesialisasi **swing trading berbasis data (quantamental)**.  
    Tugas Anda adalah menulis **analisis singkat (3-5 paragraf)** dengan karakteristik:

    1. **Faktual & Terukur** – Setiap pernyataan harus didukung angka dari data yang diberikan. Jangan gunakan opini tanpa bukti.
    2. **Membedah Transaksi** – Fokus pada arus modal (bandar proxy, net volume), struktur kepemilikan, dan konteks pasar.
    3. **Risk-Aware** – Selalu sertakan pertimbangan risiko likuiditas dan volatilitas.
    4. **Rekomendasi Tegas** – Akhiri dengan simpulan: **STRONG BUY / BUY / WATCH / AVOID** beserta alasannya.
    5. **Bahasa Indonesia formal, padat, tidak bertele-tele**.
    6. **Tidak ada promosi, tidak ada jaminan profit** – ini adalah alat bantu, bukan nasihat investasi mutlak.
    7. **Anda adalah analis independen. Anda dapat setuju atau tidak setuju dengan prediksi model, selama didukung oleh data. Jika analisis Anda berbeda, jelaskan dengan jelas mengapa.**

    PENTING: Confidence score adalah probabilitas yang diberikan model ensemble bahwa saham akan memberikan return >2% dalam 10 hari ke depan. Semakin tinggi skor, semakin yakin model akan potensi kenaikan harga.
    """

    user_prompt = f"""
    Berikut adalah data terkini saham **{ticker}** (per {datetime.now().strftime('%d %b %Y')}):

    ─────────────────────────────────────────────
    📊 **DATA TEKNIKAL & VOLUME**
    ─────────────────────────────────────────────
    • Harga Close        : {price:,.0f}
    • Open/High/Low      : {open_price:,.0f} / {high_price:,.0f} / {low_price:,.0f}
    • Rentang Intraday   : {tech_data.get('intraday_range_pct', 0):.2%}
    • Perubahan 5 Hari   : {price_change_5d:+.2%}
    • VWAP 20 hari       : {tech_data.get('vwap_20', 0):,.0f} → {bandar_status} ({dist_vwap:+.2%})
    • Net Volume 5 hari  : {helper.format_big_number(tech_data.get('net_vol_5d_sum', 0))} → {net_vol_status}
    • Volume Hari Ini    : {tech_data.get('volume', 0):,.0f} ({volume_ratio:.1f}x rata-rata 20H)
    • RSI(14)            : {tech_data.get('rsi_14', 0):.1f} → {rsi_status}
    • ATR(10)            : {tech_data.get('atr_10d', 0):.2%} (volatilitas harian rata-rata)
    • Trend              : {tech_data.get('trend', 'Sideways')}
    • Sinyal Akumulasi   : {'TERDETEKSI' if tech_data.get('accum_signal', 0) else 'TIDAK ADA'}

    ─────────────────────────────────────────────
    🏛️ **STRUKTUR KEPEMILIKAN (rilis terakhir)**
    ─────────────────────────────────────────────
    • Asing             : {profile.get('foreign_pct', 0):.2%}
    • Free Float        : {profile.get('public_pct', 0):.2%} → {likuiditas_risk}
    • Pengendali        : {profile.get('controller_pct', 0):.2%}
    • Karakteristik     : {asing_desc}

    ─────────────────────────────────────────────
    🌍 **KONTEKS PASAR**
    ─────────────────────────────────────────────
    • Market Net Ratio  : {market_data.get('market_net_ratio', 0):.4f}
    • Sentimen Pasar    : {market_data.get('market_sentiment_desc', 'Netral')}
    • MA5 Sentimen      : {market_data.get('market_ma5', 0):.4f}

    ─────────────────────────────────────────────
    🤖 **PREDIKSI MODEL**
    ─────────────────────────────────────────────
    • Confidence Score  : {prob:.2%} (probabilitas target tercapai)
    • Threshold Rekom   : {threshold:.2%} (batas minimal untuk sinyal beli)
    • Status            : {'**SINYAL BELI (DI ATAS THRESHOLD)**' if prob >= threshold else '**SINYAL TIDAK BELI**'}
    • Faktor Pendukung  : {', '.join(reasons) if reasons else 'Tidak ada faktor dominan'}

    ─────────────────────────────────────────────
    **TUGAS ANALISIS**:
    1. Evaluasi posisi harga terhadap VWAP (proxy bandar). Apakah diskon cukup menarik? Apakah ada divergensi dengan net volume?
    - Jika harga di atas VWAP namun net volume negatif, jelaskan arti divergensi ini. Apakah ini indikasi distribusi tersembunyi?
    - Seberapa kuat level VWAP sebagai support/resistance? Jika harga menembus VWAP, apa potensi pergerakannya?
    2. Interpretasi struktur kepemilikan. Apakah free float mendukung volatilitas wajar? Apakah asing sedang akumulasi?
    3. Hubungkan dengan sentimen pasar. Apakah saham ini bergerak searah atau berlawanan dengan pasar?
    4. Model memberikan confidence score {prob:.2%} yang {'berada di atas' if prob >= threshold else 'berada di bawah'} threshold, mengindikasikan {'potensi kenaikan' if prob >= threshold else 'potensi tidak mencapai target'}. 
    - **Setujukah Anda dengan sinyal model?** Jelaskan mengapa Anda setuju atau tidak setuju, berdasarkan data teknikal, volume, struktur kepemilikan, dan sentimen pasar.
    - Jika model memberikan sinyal positif meskipun net volume negatif, analisis apakah ini merupakan peluang atau jebakan (misal: distribusi tersembunyi vs shakeout).
    5. Berdasarkan sintesis data dan analisis Anda sendiri, berikan **rekomendasi final** (STRONG BUY / BUY / WATCH / AVOID). Rekomendasi ini bisa sama atau berbeda dengan model.
    6. Sebutkan **risiko utama** yang perlu diwaspadai dalam 1–2 minggu ke depan.
    7. **Jika rekomendasi BUY**:
    - Tentukan **level entry** yang disarankan.
    - Tentukan **stop loss** yang jelas.
    - Berikan **target harga** (take profit) dalam 1-2 minggu.
    8. **Jika rekomendasi WATCH**:
    - Jelaskan **kondisi spesifik** yang harus terjadi untuk berubah menjadi BUY.
    - Sebutkan **level yang jika ditembus akan mengonfirmasi pelemahan** (breakdown) yang mengarah ke AVOID.
    - Berikan perkiraan arah pergerakan jika level-level tersebut tercapai.
    9. **Jika rekomendasi AVOID**:
    - Meskipun tidak direkomendasikan, sebutkan level-level yang perlu dipantau jika investor ingin masuk (misal: penembusan resistance tertentu) sebagai sinyal pembalikan.
    """

    generate_config = types.GenerateContentConfig(
        temperature=0.2,
        system_instruction=sys_instruct,
        max_output_tokens=8192,       
    )

    model_name = 'gemini-2.5-flash' 
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=generate_config
        )
        if response.text:
            return response.text
    except Exception as e:
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=user_prompt,
                config=generate_config
            )
            if response.text:
                return response.text
        except:
            pass
    return "Layanan Gemini tidak dapat diakses saat ini."

st.set_page_config(
    page_title="AI - Stock Advisor",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    
    /* MODIFIKASI KARTU METRIC */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e6e9ef;
        /* BARIS KUNCI: Agar tooltip tidak terpotong/hilang */
        overflow: visible !important; 
    }
    
    /* Memastikan teks label berwarna gelap */
    [data-testid="stMetricLabel"] {
        color: #555555 !important;
    }
    
    /* Memastikan nilai angka berwarna gelap */
    [data-testid="stMetricValue"] {
        color: #1f1f1f !important;
    }

    /* Memastikan indikator naik/turun tebal */
    [data-testid="stMetricDelta"] {
        font-weight: bold;
    }
    
    /* TAMBAHAN: Memastikan ikon tanda tanya (?) tooltip terlihat jelas */
    [data-testid="stMetricLabel"] svg {
        fill: #555555 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Load model (cached)
@st.cache_resource
def load_ensemble_model():
    model_path = "models/model_v8_final.pkl"
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None

meta = load_ensemble_model()
if meta is None:
    st.error("❌ Model tidak ditemukan. Pastikan file model ada di folder 'models'.")
    st.stop()

# Sidebar
st.sidebar.title("MODEL ANALISA TRANSAKSI")
st.sidebar.markdown("---")
ticker = st.sidebar.text_input("Masukkan Kode Saham (Ticker):", value="BBCA").upper()
analyze_btn = st.sidebar.button("Mulai Analisis")

st.sidebar.info("""
**DO YOUR OWN RESEARCH**
""")

# - **Model Utama:** Ensemble (LGBM, CatBoost, RF)
# - **Model Sekunder:** Gemini 2.5 Flash

# Main content
st.title("📈 Stock Analysis & AI Recommendation")
st.write(f"Menganalisis data pasar secara real-time untuk **{ticker}**")


if 'analyzed' not in st.session_state:
    st.session_state['analyzed'] = False
if 'data_result' not in st.session_state:
    st.session_state['data_result'] = None


if analyze_btn:
    with st.spinner(f"🔍 Mengambil data {ticker} dan menjalankan AI..."):
        # 1. Fetch data
        df_live = helper.get_live_data(ticker)

        if df_live is not None and not df_live.empty:
            # 2. Market sentiment
            market_ratio, market_ma5 = helper.get_latest_market_sentiment()
            features_list = meta['features']
            
            # 3. Feature engineering
            df_feat = helper.calculate_features(df_live, market_ratio, market_ma5, features_list)
            
            # 4. Prediksi ensemble
            X = df_feat[features_list]
            p_lgb = meta['model_lgb'].predict_proba(X)[0, 1]
            p_cat = meta['model_cat'].predict_proba(X)[0, 1]
            p_rf = meta['model_rf'].predict_proba(X)[0, 1]
            
            w = meta['weights']
            final_prob = (w['lgb'] * p_lgb) + (w['cat'] * p_cat) + (w['rf'] * p_rf)
            threshold = meta['threshold']

            # Ekstrak nilai terbaru
            latest_price = df_feat['close'].values[0]
            dist_vwap = df_feat['price_vs_vwap'].values[0]
            rsi = df_feat['rsi_14'].values[0]
            net_vol_5d = df_feat['net_vol_5d_sum'].values[0]
            atr = df_feat['atr_10d'].values[0]
            trend = "Uptrend" if df_feat['trend_strong'].values[0] == 1 else "Downtrend/Sideways"
            accum = df_feat['accum_signal'].values[0]
            price_change_5d = df_feat['price_change_5d'].values[0]
            open_price = df_feat['open'].values[0]
            high = df_feat['high'].values[0]
            low = df_feat['low'].values[0]
            volume = df_feat['volume'].values[0]
            avg_volume_20 = df_feat['avg_volume_20'].values[0]
            volume_ratio = df_feat['volume_ratio'].values[0]
            intraday_range_pct = df_feat['intraday_range_pct'].values[0]

            # --- EKSTRAK DATA BROKER & ASING TERBARU (Hari Terakhir) ---
            try:
                print(df_live.columns)
                top_buyer_code = df_live['top_buyer_code'].values[-1]
                top_buyer_avg = df_live['top_buyer_avg'].values[-1]
                foreign_net_vol = df_live['foreign_net_vol'].values[-1]
            except Exception as e:
                # Fallback jika kolom tidak ada
                top_buyer_code = "N/A"
                top_buyer_avg = 0
                foreign_net_vol = 0

            profile_data = {
                'foreign_pct': df_feat['foreign_pct'].values[0],
                'public_pct': df_feat['public_pct'].values[0],
                'controller_pct': df_feat['controller_pct'].values[0]
            }
            tech_data = {
                'vwap_20': df_feat['vwap_20'].values[0],
                'net_vol_5d_sum': net_vol_5d,
                'rsi_14': rsi,
                'atr_10d': atr,
                'trend': trend,
                'accum_signal': accum,
                'dist_to_vwap': dist_vwap,
                'price_change_5d': price_change_5d,
                'open': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'avg_volume_20': avg_volume_20,
                'volume_ratio': volume_ratio,
                'intraday_range_pct': intraday_range_pct
            }
            market_data = {
                'market_net_ratio': market_ratio,
                'market_sentiment_desc': (
                    'Bullish' if market_ratio > 0.02 else
                    'Bearish' if market_ratio < -0.02 else 'Netral'
                ),
                'market_ma5': market_ma5
            }
            
            reasons = []
            if dist_vwap < 0: reasons.append(f"Diskon {abs(dist_vwap):.1%} dari VWAP")
            if net_vol_5d > 0: reasons.append("Net Volume positif 5 hari")
            if net_vol_5d < 0: reasons.append("Net Volume negatif 5 hari")
            if rsi < 30: reasons.append("RSI oversold")
            if rsi > 70: reasons.append("RSI overbought")
            if accum == 1: reasons.append("Sinyal akumulasi terdeteksi")
            if final_prob > threshold: reasons.append(f"Confidence {final_prob:.1%} > threshold")

            gemini_analysis = get_gemini_advice(
                ticker=ticker,
                price=latest_price,
                profile=profile_data,
                tech_data=tech_data,
                market_data=market_data,
                prob=final_prob,
                threshold=threshold,
                reasons=reasons
            )

            # --- SIMPAN KE STATE ---
            st.session_state['data_result'] = {
                'df_live': df_live,
                'latest_price': latest_price,
                'final_prob': final_prob,
                'rsi': rsi,
                'dist_vwap': dist_vwap,
                'net_vol_5d': net_vol_5d,
                'threshold': threshold,
                'gemini_analysis': gemini_analysis,
                'top_buyer_code': top_buyer_code,
                'top_buyer_avg': top_buyer_avg,
                'foreign_net_vol': foreign_net_vol
            }
            st.session_state['analyzed'] = True
            
        else:
            st.error(f"❌ Gagal mengambil data untuk {ticker}. Pastikan kode saham benar.")
            st.session_state['analyzed'] = False


# --- Render UI dari State ---
if st.session_state['analyzed'] and st.session_state['data_result'] is not None:
    
    res = st.session_state['data_result']
    df_live = res['df_live']
    latest_price = res['latest_price']
    final_prob = res['final_prob']
    rsi = res['rsi']
    dist_vwap = res['dist_vwap']
    threshold = res['threshold']
    gemini_analysis = res['gemini_analysis']
    
    # Ambil data tambahan broker & asing
    top_buyer_code = res.get('top_buyer_code', 'N/A')
    top_buyer_avg = res.get('top_buyer_avg', 0)
    foreign_net_vol = res.get('foreign_net_vol', 0)

    # --- Header metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Harga Terakhir", 
        f"Rp {latest_price:,.0f}",
        help="Harga penutupan terakhir saham ini di pasar reguler."
    )
            
    col2.metric(
        "Model Confidence", 
        f"{final_prob:.2%}",
        help="""
        Probabilitas model bahwa saham ini akan PROFIT > 2% dalam 10 hari ke depan.
        - > 50%: Sinyal Positif
        - > 70%: Sinyal Sangat Kuat
        """
    )
            
    col3.metric(
        "RSI (14)", 
        f"{rsi:.1f}",
        help=r"""
        Relative Strength Index (Momentum):
        - < 30: Oversold (Jenuh Jual) -> Potensi mantul naik
        - \> 70: Overbought (Jenuh Beli) -> Hati-hati koreksi
        - 50: Netral
        """
    )
            
    col4.metric(
        "Dist to VWAP", 
        f"{dist_vwap:+.2%}",
        delta_color="off",
        help="""
        Jarak harga saat ini vs VWAP (Volume Weighted Average Price).
        - Negatif (-): Harga 'DISKON' di bawah rata-rata modal market maker.
        - Positif (+): Harga 'MAHAL' di atas modal market maker.
        """
    )

    # --- Candlestick chart (60 hari terakhir) ---
    st.markdown("### 📊 Tren Harga & Indikator Teknikal")
    
    indicators = st.multiselect(
        "Pilih Indikator Tambahan:",
        ["VWAP"],
        default=["VWAP"]
    )

    df_plot = df_live.tail(120).copy()

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df_plot['date'],
        open=df_plot['open'], high=df_plot['high'],
        low=df_plot['low'], close=df_plot['close'],
        name="Harga"
    ))

    if "VWAP" in indicators:
        vp = df_plot['close'] * df_plot['volume']
        cum_vp = vp.rolling(20).sum()
        cum_v = df_plot['volume'].rolling(20).sum()
        vwap_series = cum_vp / (cum_v + 1e-5)
        
        fig.add_trace(go.Scatter(
            x=df_plot['date'], y=vwap_series, 
            mode='lines', name='VWAP (20)', line=dict(color='orange', width=2)
        ))

    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])] 
    )
    fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # --- STATISTIK DATA 5 HARI & BANDARMOLOGI ---
    with st.expander("📊 Statistik Pergerakan Harga (Market Summary)"):
        max_price = df_live['high'].max()
        min_price = df_live['low'].min()
        avg_vol = df_live['volume'].mean()
        total_net_vol = df_live['net_vol'].sum()
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        
        with stat_col1:
            st.markdown("**Harga Tertinggi (Periodik)**")
            st.markdown(f"### Rp {max_price:,.0f}")
            st.caption(f"Harga Terendah: Rp {min_price:,.0f}")
        
        with stat_col2:
            st.markdown("**Rata-rata Volume Harian**")
            st.markdown(f"### {avg_vol:,.0f} lembar")
        
        with stat_col3:
            st.markdown("**Total Akumulasi Net Vol**")
            color = "green" if total_net_vol > 0 else "red"
            st.markdown(f"### :{color}[{total_net_vol:,.0f}]")
            st.caption("Total Net Volume selama periode data")

        # --- TAMBAHAN INFORMASI BROKER & ASING ---
        st.markdown("---")
        st.markdown("##### Informasi Top Buyer (Data Terakhir)")
        
        brok_col1, brok_col2 = st.columns(2)
        
        with brok_col1:
            st.markdown("**Top Buyer (Broker)**")
            st.markdown(f"### {top_buyer_code}")
        
        with brok_col2:
            st.markdown("**Rata-rata Harga**")
            st.markdown(f"### Rp {top_buyer_avg:,.0f}")
        

        st.markdown("---")
        st.markdown("##### 🗓️ 5 Hari Perdagangan Terakhir")
        
        df_preview = df_live.tail(5).sort_values('date', ascending=False).copy()
        df_preview['date_str'] = df_preview['date'].dt.strftime('%d %b %Y')
        
        st.table(df_preview[['date_str', 'open', 'high', 'low', 'close', 'net_vol']].style.format({
            'open': '{:,.0f}', 'high': '{:,.0f}', 'low': '{:,.0f}', 
            'close': '{:,.0f}', 'net_vol': '{:,.0f}'
        }))
        
        st.caption("Menampilkan ringkasan statistik untuk analisis.*")
        
    # --- Left column: Model utama + Gauge ---
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("🤖 Hasil Model Utama")
        if final_prob >= threshold:
            status = "🟢 STRONG BUY"
            st.success(f"**Rekomendasi: {status}**")
        elif final_prob >= (threshold - 0.1):
            status = "🟡 WATCHLIST"
            st.warning(f"**Rekomendasi: {status}**")
        else:
            status = "🔴 AVOID"
            st.error(f"**Rekomendasi: {status}**")

        # Gauge chart
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=final_prob * 100,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Confidence Score (%)"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, threshold * 100], 'color': "lightgray"},
                    {'range': [threshold * 100, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': threshold * 100
                }
            }
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)

    # --- Right column: Gemini analysis ---
    with right_col:
        st.subheader("💡 Analisis Model Sekunder")
        st.markdown(gemini_analysis)

elif not st.session_state['analyzed']:
    st.info("👈 Masukkan kode saham di sidebar dan klik 'Mulai Analisis' untuk melihat rekomendasi AI.")