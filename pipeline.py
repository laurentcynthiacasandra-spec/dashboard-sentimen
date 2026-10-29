"""Pemrosesan unggahan Admin: ulasan mentah -> preprocessing -> pelabelan hybrid -> prediksi 2 model -> data warehouse.

Aturan yang sama dengan skrip 04_<aplikasi>.py dan 05_<aplikasi>.py (kamus dipakai apa adanya, tanpa modifikasi):
  preprocessing : case folding -> cleaning -> tokenizing (+huruf berulang) -> normalisasi kata tidak baku -> stopword Sastrawi
                  (negasi dipertahankan) -> stemming Sastrawi
  pelabelan     : skor leksikon InSet menentukan; skor 0 -> ikut rating (4-5 Positif, 1-2 Negatif);
                  rating 3 & skor 0 = netral -> dipecah (jumlah kata sentimen; bila seri -> model Complement NB tersimpan)
  prediksi      : vectorizer TF-IDF dan dua model (Complement NB, SVM linear) hasil pelatihan, dibaca dari folder model/
Model TIDAK dilatih ulang di sini, sehingga halaman Performa Algoritma tidak berubah.
"""
import os, re, datetime, urllib.request
from functools import lru_cache
import pandas as pd
from sqlalchemy import select, insert, update, delete, func
import db

BASE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE, "model")
KAMUS_URL = "https://raw.githubusercontent.com/nasalsabila/kamus-alay/master/colloquial-indonesian-lexicon.csv"
NEGASI = {"tidak", "tak", "bukan", "belum", "jangan", "tanpa", "kurang", "enggak", "nggak",
          "gak", "ga", "tdk", "blm", "engga", "ngga"}
DILINDUNGI = {"x", "tiktok", "instagram", "ig", "tt", "twitter"}
BATAS_BARIS = 2000                        # ulasan baru per unggahan (server gratis: stemming lambat)
KUNCI_APP = {"Instagram": "instagram", "TikTok": "tiktok", "X": "x"}
M_NB, M_SVM = "Naive Bayes (Complement)", "SVM (kernel linear)"
BASE_ID = 10_000_000                      # id_ulasan unggahan = BASE_ID + id_riwayat*100000 + nomor urut


class GagalProses(Exception):
    """Kesalahan yang pesannya aman ditampilkan ke Admin."""


@lru_cache(maxsize=1)
def sumber():
    """Muat kamus dan alat sekali saja (stemmer Sastrawi memerlukan beberapa detik)."""
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
    from Sastrawi.StopWordRemover.StopWordRemover import StopWordRemover
    from Sastrawi.Dictionary.ArrayDictionary import ArrayDictionary
    stemmer = StemmerFactory().create_stemmer()
    stop = [w for w in StopWordRemoverFactory().get_stop_words() if w not in NEGASI]
    sw = StopWordRemover(ArrayDictionary(stop))
    fp, fn = os.path.join(BASE, "inset_positive.tsv"), os.path.join(BASE, "inset_negative.tsv")
    if not (os.path.exists(fp) and os.path.exists(fn)):
        raise GagalProses("Berkas kamus InSet (inset_positive.tsv, inset_negative.tsv) belum ada di repositori.")
    pos = pd.read_csv(fp, sep="\t"); neg = pd.read_csv(fn, sep="\t")
    pos_d, neg_d = dict(zip(pos["word"], pos["weight"])), dict(zip(neg["word"], neg["weight"]))
    kamus, ada_kamus = {}, True
    path = os.path.join(BASE, "kamus_alay.csv")
    try:
        if not os.path.exists(path): urllib.request.urlretrieve(KAMUS_URL, path)
        k = pd.read_csv(path); k = k[(k.slang != k.formal) & (k.slang.str.len() > 1)]
        for s, f in zip(k.slang.str.lower(), k.formal.str.lower()):
            if s in DILINDUNGI or s in pos_d or s in neg_d: continue
            kamus.setdefault(s, f)
    except Exception:
        ada_kamus = False                 # tanpa internet: normalisasi dilewati (hasil sedikit berbeda)
    return dict(stemmer=stemmer, sw=sw, pos=pos_d, neg=neg_d, kamus=kamus, ada_kamus=ada_kamus)


@lru_cache(maxsize=4)
def muat_model(kunci):
    import joblib
    f = os.path.join(MODEL_DIR, f"model_{kunci}.joblib")
    if not os.path.exists(f):
        raise GagalProses(f"Model {kunci} belum tersedia (berkas model/model_{kunci}.joblib belum diunggah ke repositori).")
    b = joblib.load(f)
    if M_NB not in b["models"] or M_SVM not in b["models"]:
        raise GagalProses("Berkas model tidak memuat Complement NB dan SVM.")
    return b


def preprocess(text, s):
    t = str(text).lower()                                                  # 1. case folding
    t = re.sub(r"[^a-z\s]", " ", t)                                        # 2. cleaning
    toks = [re.sub(r"(.)\1{2,}", r"\1", w) for w in t.split()]            # 3. tokenizing + huruf berulang
    toks = [s["kamus"].get(w, w) for w in toks]                            # 4. normalisasi kata tidak baku
    t = s["sw"].remove(" ".join(toks))                                     # 5. stopword (negasi dipertahankan)
    return s["stemmer"].stem(t)                                            # 6. stemming


def hitung_skor(text, s):
    skor = n_pos = n_neg = 0
    for w in str(text).split():
        if w in s["pos"]: skor += s["pos"][w]; n_pos += 1
        if w in s["neg"]: skor += s["neg"][w]; n_neg += 1
    return skor, n_pos, n_neg


def label_rating(r): return "Positif" if r >= 4 else "Negatif" if r <= 2 else "Netral"


def tentukan(skor, n_pos, n_neg, rating):
    if skor > 0: return "Positif", "leksikon"
    if skor < 0: return "Negatif", "leksikon"
    if label_rating(rating) != "Netral": return label_rating(rating), "rating"
    if n_pos > n_neg: return "Positif", "netral_kata"
    if n_neg > n_pos: return "Negatif", "netral_kata"
    return None, "netral_model"


def baca_dan_periksa(df):
    """Rapikan kolom wajib. Mengembalikan (df_bersih, jumlah_baris_tak_valid)."""
    kurang = {"content", "score", "at"} - set(df.columns)
    if kurang: raise GagalProses("Kolom wajib tidak ditemukan: " + ", ".join(sorted(kurang)))
    d = df[["content", "score", "at"]].copy()
    d["score"] = pd.to_numeric(d["score"], errors="coerce")
    d["tgl"] = pd.to_datetime(d["at"], errors="coerce", utc=True).dt.date
    ok = d["content"].notna() & d["score"].between(1, 5) & d["tgl"].notna()
    d = d[ok].copy(); d["score"] = d["score"].astype(int)
    return d.reset_index(drop=True), int((~ok).sum())


def tanggal_terakhir(engine, id_app):
    with engine.connect() as c:
        return c.execute(select(func.max(db.dim_waktu.c.tanggal)).select_from(
            db.fact_sentimen.join(db.dim_waktu, db.dim_waktu.c.id_waktu == db.fact_sentimen.c.id_waktu))
            .where(db.fact_sentimen.c.id_aplikasi == id_app)).scalar()


def proses(d, kunci, progress=None):
    """d: hasil baca_dan_periksa (hanya ulasan baru). Mengembalikan DataFrame berlabel + prediksi dua model."""
    s = sumber(); b = muat_model(kunci)
    n = len(d); clean = []
    for i, t in enumerate(d["content"]):
        clean.append(preprocess(t, s))
        if progress and (i % 25 == 0 or i == n - 1): progress((i + 1) / n * 0.9, f"Preprocessing {i + 1}/{n}")
    d = d.copy(); d["clean_text"] = clean
    kosong = d["clean_text"].str.strip().eq("")
    n_kosong = int(kosong.sum()); d = d[~kosong].reset_index(drop=True)
    if d.empty: return d, n_kosong, s
    sk = d["clean_text"].apply(lambda t: hitung_skor(t, s))
    hl = [tentukan(a, b_, c_, r) for (a, b_, c_), r in zip(sk, d["score"])]
    d["label"] = [h[0] for h in hl]; d["sumber"] = [h[1] for h in hl]
    vec, mod = b["vectorizer"], b["models"]
    X = vec.transform(d["clean_text"])
    seri = d["label"].isna()
    if seri.any(): d.loc[seri, "label"] = mod[M_NB].predict(X[seri.values])      # model bantu: Complement NB tersimpan
    d["pred_nb"] = mod[M_NB].predict(X); d["pred_svm"] = mod[M_SVM].predict(X)
    if progress: progress(0.95, "Menyimpan ke database")
    return d, n_kosong, s


def simpan(engine, d, n_awal, n_kosong, nama_app, id_riwayat):
    """Tulis hasil ke data warehouse dalam satu transaksi (gagal = tidak ada yang tersimpan)."""
    sid = {"Positif": 1, "Negatif": 2}
    with engine.begin() as c:
        id_app = c.execute(select(db.dim_aplikasi.c.id_aplikasi).where(db.dim_aplikasi.c.nama_aplikasi == nama_app)).scalar()
        mid = {r.nama_model: r.id_model for r in c.execute(select(db.dim_model))}
        if id_app is None or M_NB not in mid or M_SVM not in mid: raise GagalProses("Dimensi aplikasi atau model belum lengkap di database.")
        wid = {r.tanggal: r.id_waktu for r in c.execute(select(db.dim_waktu))}
        baru = sorted(t for t in d["tgl"].unique() if t not in wid)
        nxt = (max(wid.values()) if wid else 0) + 1
        for t in baru: wid[t] = nxt; nxt += 1
        if baru: c.execute(insert(db.dim_waktu), [dict(id_waktu=wid[t], tanggal=t, bulan=t.month, tahun=t.year) for t in baru])
        base = BASE_ID + id_riwayat * 100_000
        rows = []
        for nm, kol in ((M_NB, "pred_nb"), (M_SVM, "pred_svm")):
            for i, r in enumerate(d.itertuples()):
                a, p = sid[r.label], sid[getattr(r, kol)]
                rows.append(dict(id_ulasan=base + i, id_aplikasi=id_app, id_waktu=wid[r.tgl], id_model=mid[nm],
                                 id_sentimen=a, id_sentimen_prediksi=p, prediksi_benar=(a == p), data_uji=False))
        for k in range(0, len(rows), 2000): c.execute(insert(db.fact_sentimen), rows[k:k + 2000])
        sm = d["sumber"].value_counts().to_dict(); n_pos = int((d["label"] == "Positif").sum()); n_neg = int((d["label"] == "Negatif").sum())
        u = dict(id_riwayat=id_riwayat, id_aplikasi=id_app, n_awal=n_awal, n_kosong=n_kosong, n_dipakai=len(d),
                 n_leksikon=sm.get("leksikon", 0), n_rating=sm.get("rating", 0), n_netral_kata=sm.get("netral_kata", 0),
                 n_netral_model=sm.get("netral_model", 0), n_positif=n_pos, n_negatif=n_neg, dibatalkan=False)
        c.execute(insert(db.unggahan), [u])
        _ubah_ringkasan(c, id_app, +1, u)
    return u


def _ubah_ringkasan(c, id_app, arah, u):
    rl = db.ringkasan_label
    c.execute(update(rl).where(rl.c.id_aplikasi == id_app).values(
        data_awal=rl.c.data_awal + arah * u["n_awal"], data_dipakai=rl.c.data_dipakai + arah * u["n_dipakai"],
        dibuang_kosong=rl.c.dibuang_kosong + arah * u["n_kosong"], label_leksikon=rl.c.label_leksikon + arah * u["n_leksikon"],
        label_rating=rl.c.label_rating + arah * u["n_rating"], netral_kata=rl.c.netral_kata + arah * u["n_netral_kata"],
        netral_model=rl.c.netral_model + arah * u["n_netral_model"], positif=rl.c.positif + arah * u["n_positif"],
        negatif=rl.c.negatif + arah * u["n_negatif"]))


def batalkan(engine, id_riwayat):
    """Hapus seluruh data dari satu unggahan dan kembalikan angka ringkasan seperti semula."""
    with engine.begin() as c:
        u = c.execute(select(db.unggahan).where(db.unggahan.c.id_riwayat == id_riwayat)).first()
        if u is None or u.dibatalkan: raise GagalProses("Unggahan tidak ditemukan atau sudah dibatalkan.")
        base = BASE_ID + id_riwayat * 100_000
        c.execute(delete(db.fact_sentimen).where(db.fact_sentimen.c.id_ulasan >= base, db.fact_sentimen.c.id_ulasan < base + 100_000))
        _ubah_ringkasan(c, u.id_aplikasi, -1, dict(u._mapping))
        pakai = select(db.fact_sentimen.c.id_waktu).distinct()
        c.execute(delete(db.dim_waktu).where(db.dim_waktu.c.id_waktu.not_in(pakai)))   # tanggal yang tidak lagi dipakai
        c.execute(update(db.unggahan).where(db.unggahan.c.id_riwayat == id_riwayat).values(dibatalkan=True))
        c.execute(update(db.riwayat_pelatihan).where(db.riwayat_pelatihan.c.id == id_riwayat).values(status="Dibatalkan", catatan="Data unggahan dihapus oleh Admin"))
