import pandas as pd
import numpy as np
import os
import joblib
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
import warnings

warnings.filterwarnings('ignore')

# --- KONFIGURASI ---
N_FOLDS = 5
RANDOM_STATE = 42

def load_data():
    data_path = "data/processed/final_dataset.csv"
    if not os.path.exists(data_path):
        print("❌ Dataset tidak ditemukan. Jalankan preprocess.py dulu!")
        return None, None, None
    
    df = pd.read_csv(data_path)
    
    # === [FIX] SESUAIKAN DENGAN NAMA DI PREPROCESS.PY ===
    feature_cols = [
        'net_top1',             # Net Volume
        'buyer_aggression',     # HAKA
        'code_buyer_retail',    # <-- Ganti nama (sebelumnya is_retail_buyer)
        'code_seller_retail',   # <-- Ganti nama (sebelumnya is_retail_seller)
        'top1_buy_vol',         # Volume Murni
        'smart_accumulation_score', # <-- Tambahkan ini! (Fitur canggih Anda sayang kalau gak dipakai)
        'retail_disguise_score',    # <-- Tambahkan ini juga!
        'panic_absorption_score'    # <-- Tambahkan ini juga!
    ]
    
    # Cek apakah semua kolom ada?
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Error: Kolom berikut hilang di CSV: {missing_cols}")
        print("   -> Coba jalankan ulang 'python preprocess.py'")
        return None, None, None

    X = df[feature_cols].values 
    y = df['target_class'].values
    return X, y, feature_cols

def search_best_blend(oof_lgb, oof_rf, y_true):
    """Mencari bobot dan threshold terbaik dari hasil OOF"""
    best_score = 0
    best_config = {'w_lgb': 0, 'w_rf': 0, 'thr': 0.5}
    
    # Grid Search Bobot (Total 1.0)
    # Kombinasi bobot (LGB, RF)
    weights = [
        (0.1, 0.9), (0.2, 0.8), (0.3, 0.7), (0.4, 0.6), 
        (0.5, 0.5), 
        (0.6, 0.4), (0.7, 0.3), (0.8, 0.2), (0.9, 0.1)
    ]
    
    thresholds = np.linspace(0.40, 0.70, 100) # Cari threshold antara 0.4 - 0.7
    
    print(f"🔎 Mencari kombinasi terbaik dari {len(weights) * len(thresholds)} kemungkinan...")
    
    for w_lgb, w_rf in weights:
        # Hitung probabilitas gabungan
        blend_prob = (w_lgb * oof_lgb) + (w_rf * oof_rf)
        
        for thr in thresholds:
            preds = (blend_prob >= thr).astype(int)
            score = f1_score(y_true, preds, average='macro')
            
            if score > best_score:
                best_score = score
                best_config = {'w_lgb': w_lgb, 'w_rf': w_rf, 'thr': thr}
                
    return best_score, best_config

def run_training():
    print("🚀 MEMULAI TRAINING: LIGHTGBM + RANDOM FOREST")
    print("============================================")
    
    X, y, feature_names = load_data()
    if X is None: return
    
    # Jika data terlalu sedikit untuk 5 fold (misal saat testing sekarang)
    if len(X) < 20:
        real_folds = 2
        print(f"⚠️ Data sedikit ({len(X)} baris). Menggunakan {real_folds} Folds.")
    else:
        real_folds = N_FOLDS
        print(f"📊 Menggunakan {real_folds}-Fold Cross Validation pada {len(X)} data.")

    # Hitung Scale Pos Weight (Untuk menyeimbangkan kelas 0 dan 1)
    neg, pos = (y == 0).sum(), (y == 1).sum()
    scale_pos_weight = neg / pos if pos > 0 else 1.0
    print(f'⚖️ Scale Pos Weight: {scale_pos_weight:.2f}')

    # Siapkan Array Kosong untuk OOF
    oof_lgb = np.zeros(len(X))
    oof_rf = np.zeros(len(X))
    
    # Siapkan List Model untuk disimpan nanti
    models_lgb = []
    models_rf = []

    kf = StratifiedKFold(n_splits=real_folds, shuffle=True, random_state=RANDOM_STATE)

    # --- LOOP TRAINING PER FOLD ---
    for fold, (tr_idx, va_idx) in enumerate(kf.split(X, y), 1):
        print(f'\n📂 Fold {fold}/{real_folds}')
        X_tr, X_va = X[tr_idx], X[va_idx]
        y_tr, y_va = y[tr_idx], y[va_idx]

        # 1. LIGHTGBM
        # Parameter statis dulu (bisa diganti hasil Optuna nanti)
        lgb_params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': -1,
            'min_child_samples': 5, # Kecilkan biar gak error di data dikit
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'scale_pos_weight': scale_pos_weight,
            'random_state': RANDOM_STATE,
            'n_jobs': -1,
            'verbosity': -1
        }
        
        dtrain = lgb.Dataset(X_tr, y_tr)
        dval = lgb.Dataset(X_va, y_va, reference=dtrain)
        
        lgb_model = lgb.train(
            lgb_params,
            dtrain,
            num_boost_round=1000,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        
        # Simpan prediksi OOF
        oof_lgb[va_idx] = lgb_model.predict(X_va)
        models_lgb.append(lgb_model) # Simpan model fold ini

        # 2. RANDOM FOREST
        # RF tidak punya early stopping native seperti GBM, jadi fit biasa
        rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            class_weight='balanced',
            random_state=RANDOM_STATE,
            n_jobs=-1
        )
        rf_model.fit(X_tr, y_tr)
        
        # Simpan prediksi OOF (Probabilitas kelas 1)
        oof_rf[va_idx] = rf_model.predict_proba(X_va)[:, 1]
        models_rf.append(rf_model)

        # Cek sekilas F1 di fold ini
        score_lgb = f1_score(y_va, (oof_lgb[va_idx] > 0.5).astype(int), average='macro')
        print(f'  -> LGB F1: {score_lgb:.4f}')

    # --- SETELAH SEMUA FOLD SELESAI ---
    print("\n🧪 Optimasi Blending & Threshold...")
    best_score, best_config = search_best_blend(oof_lgb, oof_rf, y)

    print(f'\n╔════════════════════════════════════════╗')
    print(f'║  HASIL FINAL (CHAMPION)                ║')
    print(f'╠════════════════════════════════════════╣')
    print(f'║ Bobot LightGBM     : {best_config["w_lgb"]*100}%             ║')
    print(f'║ Bobot Random Forest: {best_config["w_rf"]*100}%             ║')
    print(f'║ Threshold Ideal    : {best_config["thr"]:.4f}                ║')
    print(f'║ Final F1 Score     : {best_score:.4f}                ║')
    print(f'╚════════════════════════════════════════╝')

    # --- SIMPAN MODEL & KONFIGURASI ---
    # Kita harus menyimpan:
    # 1. Konfigurasi bobot (best_config)
    # 2. Model yang sudah dilatih (bisa pilih: simpan semua fold atau train ulang 1 model full)
    
    # Strategi Demo: Train ulang 1 model LGB dan 1 model RF pakai FULL DATA
    # dengan parameter yang sama, lalu simpan.
    
    print("\n💾 Menyimpan Model Final untuk Demo...")
    
    # Train Full LGB
    full_dtrain = lgb.Dataset(X, y)
    final_lgb = lgb.train(lgb_params, full_dtrain, num_boost_round=models_lgb[0].best_iteration)
    
    # Train Full RF
    final_rf = RandomForestClassifier(n_estimators=200, max_depth=10, class_weight='balanced', random_state=RANDOM_STATE)
    final_rf.fit(X, y)
    
    meta_data = {
        'lgb_model': final_lgb,
        'rf_model': final_rf,
        'config': best_config,
        'features': feature_names
    }
    
    os.makedirs("models", exist_ok=True)
    joblib.dump(meta_data, "models/final_blend_model.pkl")
    print("✅ Selesai! Model tersimpan di: models/final_blend_model.pkl")

if __name__ == "__main__":
    run_training()