"""ETL: memuat hasil pipeline (hasil_<app>.xlsx, ringkasan_<app>.xlsx, prediksi_<app>.csv) ke star schema.
Pakai:  python etl.py [folder_data]      (default: ./data)   -- aman diulang, data fakta dimuat ulang
"""
import sys, os, glob
import pandas as pd
from sqlalchemy import insert, delete, text
import db

APPS = {"instagram": ("Instagram", "com.instagram.android"), "tiktok": ("TikTok", "com.zhiliaoapp.musically"),
        "x": ("X", "com.twitter.android")}
MODEL_KOLOM = {"Naive Bayes (Complement)": False, "SVM (kernel linear)": False}

def main(folder):
    db.init_db()
    with db.engine.begin() as c:
        for t in [db.fact_sentimen, db.fact_evaluasi, db.ringkasan_label]: c.execute(delete(t))
        # dimension statis
        for t in [db.dim_model, db.dim_sentimen]: c.execute(delete(t))
        c.execute(delete(db.dim_aplikasi)); c.execute(delete(db.dim_waktu))
        c.execute(insert(db.dim_sentimen), [{"id_sentimen": 1, "label_sentimen": "Positif"}, {"id_sentimen": 2, "label_sentimen": "Negatif"}])
        c.execute(insert(db.dim_model), [{"id_model": i + 1, "nama_model": n, "pembanding": p} for i, (n, p) in enumerate(MODEL_KOLOM.items())])
    mid = {n: i + 1 for i, n in enumerate(MODEL_KOLOM)}; sid = {"Positif": 1, "Negatif": 2}
    waktu_id = {}; total = 0
    for aid, (key, (nama, pkg)) in enumerate(APPS.items(), 1):
        f_pred = os.path.join(folder, f"prediksi_{key}.csv")
        if not os.path.exists(f_pred): print(f"  [lewati] {nama}: {f_pred} tidak ada"); continue
        print(f"Memuat {nama} ...")
        pred = pd.read_csv(f_pred); pred["tgl"] = pd.to_datetime(pred["at"]).dt.date
        with db.engine.begin() as c:
            c.execute(insert(db.dim_aplikasi), [{"id_aplikasi": aid, "nama_aplikasi": nama, "package_name": pkg}])
            baru = [d for d in pred["tgl"].unique() if d not in waktu_id]
            for d in baru: waktu_id[d] = len(waktu_id) + 1
            if baru:
                c.execute(insert(db.dim_waktu), [{"id_waktu": waktu_id[d], "tanggal": d, "bulan": d.month, "tahun": d.year} for d in baru])
            rows = []
            for m, i_m in mid.items():
                if m not in pred.columns: continue
                sub = pd.DataFrame({"id_ulasan": pred["review_id"], "id_waktu": pred["tgl"].map(waktu_id),
                    "akt": pred["label_akhir"].map(sid), "prd": pred[m].map(sid), "uji": pred["set"].eq("uji")})
                sub["id_aplikasi"] = aid; sub["id_model"] = i_m; sub["id_sentimen"] = sub.pop("akt")
                sub["id_sentimen_prediksi"] = sub.pop("prd"); sub["prediksi_benar"] = sub["id_sentimen"] == sub["id_sentimen_prediksi"]
                sub["data_uji"] = sub.pop("uji"); rows.append(sub)
            df = pd.concat(rows); total += len(df)
            df.to_sql("fact_sentimen", c, if_exists="append", index=False, chunksize=5000, method="multi")
            # fact_evaluasi
            met = pd.read_excel(os.path.join(folder, f"hasil_{key}.xlsx"), sheet_name="Metrik")
            kes = pd.read_excel(os.path.join(folder, f"hasil_{key}.xlsx"), sheet_name="Kesimpulan")
            cm = pd.read_excel(os.path.join(folder, f"hasil_{key}.xlsx"), sheet_name="ConfusionMatrix", header=None)
            n_latih, n_uji = int(kes["Data latih"].iloc[0]), int(kes["Data uji"].iloc[0])
            evals = []
            for _, r in met.iterrows():
                nm = r["Model"]
                if nm not in mid: continue  # model di luar daftar (mis. Multinomial) tidak dimuat
                # confusion matrix dihitung dari fakta data uji (lebih andal daripada membaca sel Excel)
                f = df[(df.id_model == mid[nm]) & (df.data_uji)]
                tp = int(((f.id_sentimen == 1) & (f.id_sentimen_prediksi == 1)).sum()); fn = int(((f.id_sentimen == 1) & (f.id_sentimen_prediksi == 2)).sum())
                fp = int(((f.id_sentimen == 2) & (f.id_sentimen_prediksi == 1)).sum()); tn = int(((f.id_sentimen == 2) & (f.id_sentimen_prediksi == 2)).sum())
                evals.append({"id_aplikasi": aid, "id_model": mid[nm], "accuracy": float(r["Accuracy"]), "precision_pos": float(r["Precision (Positif)"]),
                    "recall_pos": float(r["Recall (Positif)"]), "f1_pos": float(r["F1 (Positif)"]), "macro_f1": float(r["Macro-F1"]),
                    "waktu_latih": float(r["Waktu latih (detik)"]), "terbaik": str(r.iloc[7]).strip().upper() == "YA",
                    "n_latih": n_latih, "n_uji": n_uji, "tp": tp, "fn": fn, "fp": fp, "tn": tn})
            c.execute(insert(db.fact_evaluasi), evals)
            rs = pd.read_excel(os.path.join(folder, f"ringkasan_{key}.xlsx")).iloc[0]
            c.execute(insert(db.ringkasan_label), [{"id_aplikasi": aid, "data_awal": int(rs["Data awal"]), "data_dipakai": int(rs["Data dipakai"]),
                "dibuang_kosong": int(rs["Dibuang (teks kosong)"]), "label_leksikon": int(rs["Label dari leksikon"]), "label_rating": int(rs["Label dari rating"]),
                "netral_kata": int(rs["Netral dipecah (kata sentimen)"]), "netral_model": int(rs["Netral dipecah (model bantu)"]),
                "positif": int(rs["Positif"]), "negatif": int(rs["Negatif"]), "sejalan_persen": float(rs["% Sejalan rating-leksikon"])}])
    print(f"SELESAI. {total} baris fakta dimuat.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "data"))
