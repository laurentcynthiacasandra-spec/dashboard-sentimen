"""Menyiapkan berkas model untuk dashboard.
Jalankan DI FOLDER YANG SAMA dengan model_instagram.joblib, model_tiktok.joblib, dan model_x.joblib (atau model_twitter.joblib)
hasil 05_<aplikasi>.py:
    python siapkan_model.py
Hasil: folder model/ berisi model_instagram.joblib, model_tiktok.joblib, model_x.joblib versi ringkas
(hanya TF-IDF + Complement NB + SVM; tanpa Multinomial). Unggah isi folder model/ ke GitHub.
"""
import os, sys, joblib, sklearn
NAMA = {"instagram": ["instagram"], "tiktok": ["tiktok"], "x": ["x", "twitter"]}
M = ["Naive Bayes (Complement)", "SVM (kernel linear)"]
os.makedirs("model", exist_ok=True); ada = 0
for kunci, calon in NAMA.items():
    f = next((f"model_{c}.joblib" for c in calon if os.path.exists(f"model_{c}.joblib")), None)
    if not f: print(f"[lewati] model untuk {kunci} tidak ditemukan"); continue
    b = joblib.load(f)
    vec = b["vectorizer"]; vec.stop_words_ = None                    # atribut besar yang tidak diperlukan untuk prediksi
    out = {"vectorizer": vec, "models": {m: b["models"][m] for m in M}}
    tujuan = os.path.join("model", f"model_{kunci}.joblib")
    joblib.dump(out, tujuan, compress=9)
    print(f"{f} -> {tujuan}  ({os.path.getsize(tujuan) / 1024 / 1024:.1f} MB)"); ada += 1
print(f"\nSelesai: {ada} model. Versi scikit-learn di komputermu: {sklearn.__version__}")
print(f"Pastikan requirements.txt berisi baris:  scikit-learn=={sklearn.__version__}")
