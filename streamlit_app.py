import os
from datetime import date

import bcrypt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="Dashboard Analisis Sentimen",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

HD = "#175A85"
HD_DARK = "#0F3F5E"
POS = "#3F8A1E"
NEG = "#D94545"
MUTED = "#6B7A8F"
BORDER = "#E5DED9"
IG_COLOR = "#8B5CF6"
TT_COLOR = "#14B8A6"
X_COLOR = "#1E3A5F"

# Waktu latih model (detik) — dari hasil training sebelumnya
WAKTU_LATIH = {
    ("Instagram", "Naive Bayes"): 0.4, ("Instagram", "SVM"): 57.5,
    ("Instagram", "Naive Bayes (Complement)"): 0.4, ("Instagram", "SVM (kernel linear)"): 57.5,
    ("TikTok", "Naive Bayes"): 0.3, ("TikTok", "SVM"): 64.9,
    ("TikTok", "Naive Bayes (Complement)"): 0.3, ("TikTok", "SVM (kernel linear)"): 64.9,
    ("X", "Naive Bayes"): 0.3, ("X", "SVM"): 50.4,
    ("X", "Naive Bayes (Complement)"): 0.3, ("X", "SVM (kernel linear)"): 50.4,
}


def warna_aplikasi(nama: str) -> str:
    n = nama.lower()
    if "insta" in n: return IG_COLOR
    if "tik" in n: return TT_COLOR
    return X_COLOR


# CSS
st.markdown(
    """
    <style>
    header, footer, #MainMenu {visibility: hidden;}
    .stApp {background: #F4F0EE;}
    .block-container {padding-top: 1.5rem !important; padding-bottom: 2.5rem; max-width: 1400px !important;}

    [data-testid="stSidebar"] {background: #FFFFFF; border-right: 1px solid #E5DED9;}
    [data-testid="stSidebar"] > div {padding-top: 1rem;}

    .sidebar-brand {
        color: #175A85; font-weight: 700; font-size: 1.1rem;
        padding: 0.4rem 0.4rem 1rem 0.4rem; border-bottom: 1px solid #E5DED9;
        margin-bottom: 0.6rem;
    }

    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
        display: flex; flex-direction: column; gap: 4px; padding: 0;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background: transparent !important; border: none !important;
        padding: 0.6rem 0.9rem !important; border-radius: 6px !important;
        margin: 0 !important; cursor: pointer; font-weight: 500;
        color: #333 !important;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {background: #F4F0EE !important;}
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {
        background: #175A85 !important; color: white !important;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {display: none !important;}
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:last-child p {color: inherit !important; margin: 0;}

    .main .stRadio > div[role="radiogroup"] {gap: 6px; flex-wrap: wrap; margin-bottom: 0.3rem;}
    .main .stRadio > div[role="radiogroup"] > label {
        background: #FFFFFF !important; border: 1px solid #E5DED9 !important;
        padding: 0.4rem 1.1rem !important; border-radius: 20px !important;
        margin: 0 !important; cursor: pointer; font-weight: 500;
        color: #6B7A8F !important;
    }
    .main .stRadio > div[role="radiogroup"] > label:hover {background: #F8F5F3 !important;}
    .main .stRadio > div[role="radiogroup"] > label:has(input:checked) {
        background: #175A85 !important; color: white !important; border-color: #175A85 !important;
    }
    .main .stRadio > div[role="radiogroup"] > label > div:first-child {display: none !important;}
    .main .stRadio > div[role="radiogroup"] > label > div:last-child p {color: inherit !important; margin: 0;}

    .page-title {color: #0F3F5E; font-size: 1.7rem; font-weight: 700; margin: 0 0 1rem 0;}

    .metrik-kecil {
        background: #FFFFFF; padding: 0.7rem 0.9rem;
        border-radius: 8px; border: 1px solid #E5DED9;
        border-top: 3px solid #175A85;
    }
    .metrik-kecil-label {color: #6B7A8F; font-size: 0.72rem; font-weight: 600;}
    .metrik-kecil-nilai {font-size: 1.3rem; font-weight: 700; color: #0F3F5E; margin-top: 0.15rem; line-height: 1.1;}
    .metrik-kecil-sub {color: #6B7A8F; font-size: 0.72rem; margin-top: 0.1rem;}

    .kartu-app {
        background: #FFFFFF; padding: 1.2rem 1.3rem;
        border-radius: 10px; border: 1px solid #E5DED9;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04); min-height: 230px;
    }
    .kartu-app-nama {font-size: 1.5rem; font-weight: 700; margin: 0;}
    .kartu-app-pct {font-size: 2.4rem; font-weight: 700; margin: 0.8rem 0 0.1rem 0; line-height: 1;}
    .kartu-app-pos {color: #6B7A8F; font-size: 0.95rem; font-weight: 500; margin-bottom: 0.7rem;}
    .mini-bar {display: flex; width: 100%; height: 10px; border-radius: 4px; overflow: hidden; margin-bottom: 0.7rem;}
    .kartu-app-stat {color: #6B7A8F; font-size: 0.82rem;}

    .kartu {
        background: #FFFFFF; padding: 1.1rem 1.3rem;
        border-radius: 8px; border: 1px solid #E5DED9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        margin-bottom: 1rem;
    }
    .kartu-judul {color: #0F3F5E; font-weight: 700; font-size: 1.05rem; margin-bottom: 0.7rem;}

    .insight {display: flex; gap: 0.6rem; padding: 0.3rem 0; align-items: flex-start;}
    .insight-dot {width: 7px; height: 7px; border-radius: 50%; background: #175A85; margin-top: 0.5rem; flex-shrink: 0;}
    .insight-text {font-size: 0.92rem; color: #333; line-height: 1.5;}

    /* Banner kuning untuk insight Perbandingan */
    .banner-insight {
        background: #FFF7E0; border: 1px solid #F0D890;
        color: #5F4B00; padding: 0.9rem 1.1rem;
        border-radius: 8px; margin: 1rem 0;
        font-size: 0.93rem;
    }
    .banner-insight b {color: #0F3F5E;}

    /* Info box biru */
    .info-biru {
        background: #E8F1F7; border: 1px solid #B9D4E6;
        color: #0F3F5E; padding: 0.9rem 1.1rem;
        border-radius: 8px; margin: 1rem 0; font-size: 0.92rem;
    }

    .login-card {
        background: #FFFFFF; padding: 2rem 1.8rem; border-radius: 12px;
        border: 1px solid #E5DED9; box-shadow: 0 6px 24px rgba(0,0,0,0.08);
        max-width: 480px; margin: 2.5rem auto;
    }
    .login-title {color: #0F3F5E; text-align: left; font-size: 2.1rem; font-weight: 800; margin: 0 0 0.3rem 0; line-height: 1.1;}
    .login-subtitle {color: #6B7A8F; text-align: left; font-size: 0.95rem; margin-bottom: 1.4rem;}

    .stButton > button {border-radius: 6px; font-weight: 600;}
    .stButton > button[kind="primary"],
    .stForm button[kind="primaryFormSubmit"] {
        background-color: #175A85 !important; border-color: #175A85 !important; color: white !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stForm button[kind="primaryFormSubmit"]:hover {
        background-color: #0F3F5E !important; border-color: #0F3F5E !important;
    }

    .stTable thead tr th {background: #E8F1F7; color: #0F3F5E; font-weight: 700; font-size: 0.85rem;}
    .stTable tbody tr td {font-size: 0.86rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Koneksi basis data
# ---------------------------------------------------------------------------
def _get_dsn() -> str:
    try: return st.secrets["DATABASE_URL"]
    except Exception: return os.environ["DATABASE_URL"]


def _buat_koneksi():
    return psycopg2.connect(_get_dsn(), sslmode="require")


def get_conn():
    conn = st.session_state.get("_db_conn")
    if conn is None or getattr(conn, "closed", 1):
        conn = _buat_koneksi()
        st.session_state["_db_conn"] = conn
    else:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1"); cur.fetchone()
        except Exception:
            try: conn.close()
            except Exception: pass
            conn = _buat_koneksi()
            st.session_state["_db_conn"] = conn
    return conn


def kueri(sql: str, params: tuple = ()) -> pd.DataFrame:
    for percobaan in range(2):
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [d[0] for d in cur.description]
                data = cur.fetchall()
            return pd.DataFrame(data, columns=cols)
        except (psycopg2.InterfaceError, psycopg2.OperationalError):
            try: conn.close()
            except Exception: pass
            st.session_state.pop("_db_conn", None)
            if percobaan == 1: raise
        except Exception:
            try: conn.rollback()
            except Exception: pass
            raise
    return pd.DataFrame()


def eksekusi(sql: str, params: tuple = ()) -> None:
    for percobaan in range(2):
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
            conn.commit()
            return
        except (psycopg2.InterfaceError, psycopg2.OperationalError):
            try: conn.close()
            except Exception: pass
            st.session_state.pop("_db_conn", None)
            if percobaan == 1: raise
        except Exception:
            try: conn.rollback()
            except Exception: pass
            raise


# ---------------------------------------------------------------------------
# Autentikasi
# ---------------------------------------------------------------------------
def masuk(username: str, password: str):
    df = kueri(
        "SELECT id_user, username, password_hash, role FROM users WHERE username = %s",
        (username.strip(),),
    )
    if df.empty: return None
    row = df.iloc[0]
    try:
        cocok = bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8"))
    except Exception:
        cocok = False
    if not cocok: return None
    return {"id_user": int(row["id_user"]), "username": row["username"], "role": row["role"]}


def daftar(username: str, password: str, konfirmasi: str):
    username = username.strip()
    if len(username) < 3: return False, "Username minimal 3 karakter."
    if len(password) < 6: return False, "Password minimal 6 karakter."
    if password != konfirmasi: return False, "Konfirmasi password tidak cocok."
    ada = kueri("SELECT 1 FROM users WHERE username = %s", (username,))
    if not ada.empty: return False, "Username sudah terpakai."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    eksekusi(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'Pengguna')",
        (username, hashed),
    )
    return True, "Akun berhasil dibuat. Silakan masuk."


def tambah_akun(username: str, password: str, role: str):
    username = username.strip()
    if len(username) < 3: return False, "Username minimal 3 karakter."
    if len(password) < 6: return False, "Password minimal 6 karakter."
    if role not in ("Admin", "Pengguna"): return False, "Peran tidak valid."
    ada = kueri("SELECT 1 FROM users WHERE username = %s", (username,))
    if not ada.empty: return False, "Username sudah terpakai."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    eksekusi(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
        (username, hashed, role),
    )
    return True, f"Akun {username} berhasil dibuat sebagai {role}."


def ubah_akun(id_user: int, password_baru: str = "", role_baru: str = ""):
    if password_baru:
        if len(password_baru) < 6: return False, "Password minimal 6 karakter."
        hashed = bcrypt.hashpw(password_baru.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        eksekusi("UPDATE users SET password_hash = %s WHERE id_user = %s", (hashed, id_user))
    if role_baru:
        if role_baru not in ("Admin", "Pengguna"): return False, "Peran tidak valid."
        eksekusi("UPDATE users SET role = %s WHERE id_user = %s", (role_baru, id_user))
    return True, "Akun berhasil diubah."


def hapus_akun(id_user: int):
    try:
        eksekusi("DELETE FROM users WHERE id_user = %s", (id_user,))
        return True, "Akun dihapus."
    except Exception as e:
        return False, f"Gagal menghapus akun: {e}"


# ---------------------------------------------------------------------------
# Kueri data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def model_utama_id() -> int:
    df = kueri("SELECT id_model FROM dim_model WHERE COALESCE(pembanding, FALSE) = FALSE ORDER BY id_model LIMIT 1")
    if not df.empty: return int(df.iloc[0]["id_model"])
    df2 = kueri("SELECT MIN(id_model) AS id_min FROM fact_sentimen")
    return int(df2.iloc[0]["id_min"]) if not df2.empty else 1


@st.cache_data(ttl=300, show_spinner=False)
def daftar_model() -> list:
    df = kueri("SELECT nama_model FROM dim_model ORDER BY nama_model")
    return df["nama_model"].tolist()


@st.cache_data(ttl=300, show_spinner=False)
def daftar_tahun() -> list:
    df = kueri(
        "SELECT DISTINCT w.tahun AS tahun FROM fact_sentimen f "
        "JOIN dim_waktu w ON w.id_waktu = f.id_waktu ORDER BY w.tahun"
    )
    return [int(t) for t in df["tahun"].dropna().unique()]


@st.cache_data(ttl=300, show_spinner=False)
def ringkasan_global() -> dict:
    idm = model_utama_id()
    df = kueri(
        """
        SELECT a.nama_aplikasi AS aplikasi, s.label_sentimen AS label, COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        WHERE f.id_model = %s
        GROUP BY a.nama_aplikasi, s.label_sentimen
        """,
        (idm,),
    )
    df["label"] = df["label"].str.strip().str.title()
    total_rincian = df.groupby("aplikasi")["jumlah"].sum().reset_index().rename(columns={"jumlah": "total_app"})
    df = df.merge(total_rincian, on="aplikasi")
    total = int(total_rincian["total_app"].sum())
    positif = int(df[df["label"] == "Positif"]["jumlah"].sum())
    pos_pct = (positif / total * 100) if total else 0.0
    aplikasi = sorted(df["aplikasi"].unique())
    tgl = kueri("SELECT MAX(w.tanggal) AS mx FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu").iloc[0]["mx"]
    return {
        "total": total, "positif_pct": pos_pct,
        "jumlah_aplikasi": len(aplikasi), "aplikasi": aplikasi,
        "rincian": df, "tanggal_terbaru": tgl,
    }


@st.cache_data(ttl=300, show_spinner=False)
def metrik_model() -> pd.DataFrame:
    df = kueri(
        """
        SELECT a.nama_aplikasi AS aplikasi, m.nama_model AS model,
               s_akt.label_sentimen AS aktual, s_pre.label_sentimen AS prediksi,
               COUNT(*) AS n
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_model m ON m.id_model = f.id_model
        JOIN dim_sentimen s_akt ON s_akt.id_sentimen = f.id_sentimen
        JOIN dim_sentimen s_pre ON s_pre.id_sentimen = f.id_sentimen_prediksi
        WHERE f.data_uji = TRUE
        GROUP BY a.nama_aplikasi, m.nama_model, s_akt.label_sentimen, s_pre.label_sentimen
        """
    )
    if df.empty: return df
    df["aktual"] = df["aktual"].str.strip().str.title()
    df["prediksi"] = df["prediksi"].str.strip().str.title()
    return df


def hitung_metrik(cm: dict) -> dict:
    tp = cm.get(("Positif", "Positif"), 0)
    fn = cm.get(("Positif", "Negatif"), 0)
    fp = cm.get(("Negatif", "Positif"), 0)
    tn = cm.get(("Negatif", "Negatif"), 0)
    total = tp + fn + fp + tn
    acc = (tp + tn) / total if total else 0.0
    def _prf(tp_, fp_, fn_):
        p = tp_ / (tp_ + fp_) if (tp_ + fp_) else 0.0
        r = tp_ / (tp_ + fn_) if (tp_ + fn_) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        return p, r, f1
    p_pos, r_pos, f1_pos = _prf(tp, fp, fn)
    p_neg, r_neg, f1_neg = _prf(tn, fn, fp)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": acc,
        "precision_pos": p_pos, "recall_pos": r_pos, "f1_pos": f1_pos,
        "precision_neg": p_neg, "recall_neg": r_neg, "f1_neg": f1_neg,
        "macro_f1": (f1_pos + f1_neg) / 2,
    }


@st.cache_data(ttl=300, show_spinner=False)
def performa_semua() -> pd.DataFrame:
    df = metrik_model()
    if df.empty: return df
    baris = []
    for (app, model), grup in df.groupby(["aplikasi", "model"]):
        cm = {(a, p): int(n) for a, p, n in zip(grup["aktual"], grup["prediksi"], grup["n"])}
        baris.append({"aplikasi": app, "model": model, **hitung_metrik(cm)})
    df_perf = pd.DataFrame(baris)
    df_perf["waktu_latih"] = df_perf.apply(
        lambda r: WAKTU_LATIH.get((r["aplikasi"], r["model"]), None), axis=1
    )
    return df_perf


@st.cache_data(ttl=300, show_spinner=False)
def rentang_tanggal(aplikasi: str) -> tuple:
    idm = model_utama_id()
    if aplikasi == "Semua" or aplikasi == "Semua aplikasi":
        df = kueri(
            "SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx "
            "FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu WHERE f.id_model = %s",
            (idm,),
        )
    else:
        df = kueri(
            "SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx "
            "FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu "
            "JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi "
            "WHERE f.id_model = %s AND a.nama_aplikasi = %s",
            (idm, aplikasi),
        )
    return df.iloc[0]["mn"], df.iloc[0]["mx"]


@st.cache_data(ttl=300, show_spinner=False)
def sentimen_bulanan(aplikasi: str, dari, sampai, tahun) -> pd.DataFrame:
    """Jumlah ulasan positif dan negatif per bulan per aplikasi."""
    idm = model_utama_id()
    cond = []
    parm = [idm]
    if aplikasi != "Semua" and aplikasi != "Semua aplikasi":
        cond.append("a.nama_aplikasi = %s"); parm.append(aplikasi)
    if tahun != "Semua" and tahun != "Semua tahun":
        cond.append("w.tahun = %s"); parm.append(int(tahun))
    if dari and sampai:
        cond.append("w.tanggal BETWEEN %s AND %s"); parm.extend([dari, sampai])
    wh = (" AND " + " AND ".join(cond)) if cond else ""
    sql = f"""
        SELECT a.nama_aplikasi AS aplikasi,
               TO_CHAR(DATE_TRUNC('month', w.tanggal), 'YYYY-MM') AS bulan,
               s.label_sentimen AS label,
               COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        JOIN dim_waktu w ON w.id_waktu = f.id_waktu
        WHERE f.id_model = %s {wh}
        GROUP BY a.nama_aplikasi, bulan, s.label_sentimen
        ORDER BY bulan
    """
    df = kueri(sql, tuple(parm))
    if not df.empty:
        df["label"] = df["label"].str.strip().str.title()
    return df


@st.cache_data(ttl=300, show_spinner=False)
def sentimen_tersaring(aplikasi: str, dari, sampai, tahun) -> pd.DataFrame:
    """Hitung sentimen per aplikasi dengan filter."""
    idm = model_utama_id()
    cond = []
    parm = [idm]
    if aplikasi != "Semua" and aplikasi != "Semua aplikasi":
        cond.append("a.nama_aplikasi = %s"); parm.append(aplikasi)
    if tahun != "Semua" and tahun != "Semua tahun":
        cond.append("w.tahun = %s"); parm.append(int(tahun))
    if dari and sampai:
        cond.append("w.tanggal BETWEEN %s AND %s"); parm.extend([dari, sampai])
    wh = (" AND " + " AND ".join(cond)) if cond else ""
    sql = f"""
        SELECT a.nama_aplikasi AS aplikasi, s.label_sentimen AS label, COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        JOIN dim_waktu w ON w.id_waktu = f.id_waktu
        WHERE f.id_model = %s {wh}
        GROUP BY a.nama_aplikasi, s.label_sentimen
    """
    df = kueri(sql, tuple(parm))
    if not df.empty: df["label"] = df["label"].str.strip().str.title()
    return df


@st.cache_data(ttl=60, show_spinner=False)
def riwayat_unggahan() -> pd.DataFrame:
    try:
        return kueri(
            """
            SELECT r.id, r.waktu, u.username, r.aplikasi, r.berkas,
                   r.jumlah_baris, r.status, r.catatan
            FROM riwayat_pelatihan r JOIN users u ON u.id_user = r.id_user
            ORDER BY r.waktu DESC LIMIT 100
            """
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def daftar_pengguna() -> pd.DataFrame:
    try:
        return kueri("SELECT id_user AS id, username, role AS peran FROM users ORDER BY id_user")
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Komponen
# ---------------------------------------------------------------------------
def page_title(judul: str) -> None:
    st.markdown(f'<div class="page-title">{judul}</div>', unsafe_allow_html=True)


def metrik_kecil(label: str, nilai: str, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="metrik-kecil">
            <div class="metrik-kecil-label">{label}</div>
            <div class="metrik-kecil-nilai">{nilai}</div>
            <div class="metrik-kecil-sub">{sub or '&nbsp;'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kartu_aplikasi(nama: str, positif: int, negatif: int, total: int) -> None:
    pct = (positif / total * 100) if total else 0
    warna = warna_aplikasi(nama)
    pct_str = f"{pct:.1f}%".replace(".", ",")
    pos_str = f"{positif:,}".replace(",", ".")
    neg_str = f"{negatif:,}".replace(",", ".")
    tot_str = f"{total:,}".replace(",", ".")
    st.markdown(
        f"""
        <div class="kartu-app">
            <div class="kartu-app-nama" style="color:{warna};">{nama}</div>
            <div class="kartu-app-pct" style="color:{HD_DARK};">{pct_str}</div>
            <div class="kartu-app-pos">positif</div>
            <div class="mini-bar">
                <div style="width:{pct}%; background:{POS};"></div>
                <div style="width:{100-pct}%; background:{NEG};"></div>
            </div>
            <div class="kartu-app-stat">
                {pos_str} positif · {neg_str} negatif · {tot_str} ulasan
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mulai_kartu(judul: str) -> None:
    st.markdown(f'<div class="kartu"><div class="kartu-judul">{judul}</div>', unsafe_allow_html=True)


def tutup_kartu() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def info_biru(teks: str) -> None:
    st.markdown(f'<div class="info-biru">{teks}</div>', unsafe_allow_html=True)


def banner_insight(teks_html: str) -> None:
    st.markdown(f'<div class="banner-insight">{teks_html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Ringkasan
# ---------------------------------------------------------------------------
def halaman_ringkasan() -> None:
    page_title("Ringkasan Insight Utama")
    data = ringkasan_global()
    tgl_str = data["tanggal_terbaru"].strftime("%Y-%m-%d") if pd.notna(data["tanggal_terbaru"]) else "-"

    k1, k2, k3, k4 = st.columns(4)
    with k1: metrik_kecil("Total ulasan dianalisis", f"{data['total']:,}".replace(",", "."), f"{data['jumlah_aplikasi']} aplikasi")
    with k2: metrik_kecil("Rata-rata sentimen positif", f"{data['positif_pct']:.1f}%".replace(".", ","), "dari seluruh ulasan")
    with k3: metrik_kecil("Model terbaik", "SVM", "berdasarkan macro-F1")
    with k4: metrik_kecil("Data terakhir", tgl_str, "tanggal ulasan terbaru")

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    rincian = data["rincian"]
    cols = st.columns(len(data["aplikasi"]))
    for i, app in enumerate(data["aplikasi"]):
        sub = rincian[rincian["aplikasi"] == app]
        positif = int(sub[sub["label"] == "Positif"]["jumlah"].sum())
        negatif = int(sub[sub["label"] == "Negatif"]["jumlah"].sum())
        total = int(sub["total_app"].max()) if not sub.empty else (positif + negatif)
        with cols[i]: kartu_aplikasi(app, positif, negatif, total)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    col_bar, col_pie = st.columns([1.1, 1])
    pos_app = rincian[rincian["label"] == "Positif"].copy()
    pos_app["pct"] = (pos_app["jumlah"] / pos_app["total_app"] * 100).round(1)
    pos_app = pos_app.sort_values("aplikasi")

    with col_bar:
        mulai_kartu("Persentase Sentimen Positif per Aplikasi")
        warna_app = [warna_aplikasi(a) for a in pos_app["aplikasi"]]
        fig = go.Figure(go.Bar(
            x=pos_app["pct"], y=pos_app["aplikasi"], orientation="h",
            marker_color=warna_app,
            text=pos_app["pct"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
            textposition="outside", textfont=dict(size=12, color=HD_DARK),
        ))
        fig.update_layout(
            xaxis=dict(range=[0, 100], title="% positif", showgrid=True, gridcolor="#eee"),
            yaxis=dict(title="", tickfont=dict(size=13)),
            height=280, margin=dict(l=10, r=40, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    with col_pie:
        mulai_kartu("Distribusi Sentimen Keseluruhan")
        pos_total = int(rincian[rincian["label"] == "Positif"]["jumlah"].sum())
        neg_total = int(rincian[rincian["label"] == "Negatif"]["jumlah"].sum())
        fig = go.Figure(data=[go.Pie(
            labels=[f"Positif ({pos_total:,})".replace(",", "."),
                    f"Negatif ({neg_total:,})".replace(",", ".")],
            values=[pos_total, neg_total],
            marker=dict(colors=[POS, NEG], line=dict(color="white", width=2)),
            hole=0.55, textinfo="none",
        )])
        fig.update_layout(
            margin=dict(l=20, r=20, t=10, b=30), height=280,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=12)),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    mulai_kartu("Insight Utama")
    if len(pos_app) >= 1:
        tgi = pos_app.sort_values("pct", ascending=False).iloc[0]
        trd = pos_app.sort_values("pct", ascending=True).iloc[0]
        t1 = f"{tgi['pct']:.1f}%".replace(".", ",")
        t2 = f"{trd['pct']:.1f}%".replace(".", ",")
        st.markdown(
            f'<div class="insight"><div class="insight-dot"></div>'
            f'<div class="insight-text"><b>{tgi["aplikasi"]}</b> memiliki proporsi sentimen positif tertinggi '
            f'({t1}), sedangkan <b>{trd["aplikasi"]}</b> terendah ({t2}).</div></div>',
            unsafe_allow_html=True,
        )
    perf = performa_semua()
    for app in data["aplikasi"]:
        sub_app = perf[perf["aplikasi"] == app].sort_values("macro_f1", ascending=False)
        if not sub_app.empty:
            tb = sub_app.iloc[0]
            f1 = f"{tb['macro_f1']:.4f}".replace(".", ",")
            st.markdown(
                f'<div class="insight"><div class="insight-dot"></div>'
                f'<div class="insight-text">Pada <b>{app}</b>, model terbaik adalah <b>{tb["model"]}</b> (macro-F1 {f1}).</div></div>',
                unsafe_allow_html=True,
            )
    tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Perbandingan Sentimen
# ---------------------------------------------------------------------------
def halaman_sentimen() -> None:
    page_title("Perbandingan Sentimen")
    data = ringkasan_global()

    mulai_kartu("Filter")
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    with c1:
        aplikasi = st.selectbox("Aplikasi", ["Semua aplikasi"] + data["aplikasi"], key="fs_app")
    with c2:
        tahun_opsi = ["Semua tahun"] + [str(t) for t in daftar_tahun()]
        tahun = st.selectbox("Tahun", tahun_opsi, key="fs_tahun")
    mn, mx = rentang_tanggal(aplikasi)
    with c3:
        dari = st.date_input("Dari tanggal", value=None, min_value=mn, max_value=mx,
                             key="fs_dari", format="DD/MM/YYYY")
    with c4:
        sampai = st.date_input("Sampai tanggal", value=None, min_value=mn, max_value=mx,
                               key="fs_sampai", format="DD/MM/YYYY")

    c5, c6, c7 = st.columns([1.5, 1.5, 1])
    with c5:
        sumber = st.selectbox(
            "Sumber label",
            ["Hasil pelabelan (semua ulasan)"],
            key="fs_sumber",
        )
    with c6:
        model_opsi = ["Semua algoritma"] + daftar_model()
        model = st.selectbox("Algoritma", model_opsi, key="fs_model")
    with c7:
        st.write("")
        st.write("")
        if st.button("Atur ulang", use_container_width=True):
            for k in ["fs_app", "fs_tahun", "fs_dari", "fs_sampai", "fs_sumber", "fs_model"]:
                st.session_state.pop(k, None)
            st.rerun()
    tutup_kartu()

    if dari and sampai and dari > sampai:
        st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'.")
        return

    df = sentimen_tersaring(aplikasi, dari, sampai, tahun)
    if df.empty:
        st.warning("Tidak ada ulasan pada filter ini.")
        return
    pivot = df.pivot(index="aplikasi", columns="label", values="jumlah").fillna(0)
    for k in ["Positif", "Negatif"]:
        if k not in pivot.columns: pivot[k] = 0
    pivot["Total"] = pivot["Positif"] + pivot["Negatif"]
    pivot["Pos_pct"] = (pivot["Positif"] / pivot["Total"] * 100).round(1)
    pivot["Neg_pct"] = (pivot["Negatif"] / pivot["Total"] * 100).round(1)
    pivot = pivot.reset_index()

    # Banner insight
    if len(pivot) >= 2:
        tgi = pivot.sort_values("Pos_pct", ascending=False).iloc[0]
        trd = pivot.sort_values("Pos_pct", ascending=True).iloc[0]
        selisih = tgi["Pos_pct"] - trd["Pos_pct"]
        periode = f"tahun {tahun}" if tahun != "Semua tahun" else "seluruh periode"
        banner_insight(
            f"<b>Pada {periode}</b>, sentimen positif tertinggi ada pada "
            f"<b>{tgi['aplikasi']}</b> ({str(tgi['Pos_pct']).replace('.', ',')}%), "
            f"sedangkan terendah <b>{trd['aplikasi']}</b> ({str(trd['Pos_pct']).replace('.', ',')}%). "
            f"Selisih {str(round(selisih, 1)).replace('.', ',')} poin."
        )

    col_a, col_b = st.columns(2)
    with col_a:
        mulai_kartu("Proporsi Sentimen Positif vs Negatif")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Positif", x=pivot["aplikasi"], y=pivot["Pos_pct"], marker_color=POS,
        ))
        fig.add_trace(go.Bar(
            name="Negatif", x=pivot["aplikasi"], y=pivot["Neg_pct"], marker_color=NEG,
        ))
        fig.update_layout(
            barmode="stack",
            xaxis=dict(title="", tickfont=dict(size=13)),
            yaxis=dict(title="", range=[0, 100], ticksuffix="%", tickfont=dict(size=11),
                       showgrid=True, gridcolor="#eee"),
            height=360, margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    with col_b:
        mulai_kartu("Tren Jumlah Ulasan per Bulan")
        tren = sentimen_bulanan(aplikasi, dari, sampai, tahun)
        if tren.empty:
            st.caption("Tidak ada data untuk filter ini.")
        else:
            fig = go.Figure()
            for app in sorted(tren["aplikasi"].unique()):
                warna = warna_aplikasi(app)
                pos_s = tren[(tren["aplikasi"] == app) & (tren["label"] == "Positif")].sort_values("bulan")
                neg_s = tren[(tren["aplikasi"] == app) & (tren["label"] == "Negatif")].sort_values("bulan")
                fig.add_trace(go.Scatter(
                    x=pos_s["bulan"], y=pos_s["jumlah"], mode="lines+markers",
                    name=f"{app} (Positif)", line=dict(color=warna, width=2),
                    marker=dict(size=6),
                ))
                fig.add_trace(go.Scatter(
                    x=neg_s["bulan"], y=neg_s["jumlah"], mode="lines+markers",
                    name=f"{app} (Negatif)", line=dict(color=warna, width=2, dash="dash"),
                    marker=dict(size=6),
                ))
            fig.update_layout(
                xaxis=dict(title="", tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(title="", tickfont=dict(size=11), showgrid=True, gridcolor="#eee"),
                height=360, margin=dict(l=10, r=10, t=10, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=9)),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    mulai_kartu("Rincian")
    tampil = pivot[["aplikasi", "Positif", "Negatif", "Total", "Pos_pct"]].copy()
    tampil.columns = ["Aplikasi", "Positif", "Negatif", "Total", "% Positif"]
    tampil["Positif"] = tampil["Positif"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    tampil["Negatif"] = tampil["Negatif"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    tampil["Total"] = tampil["Total"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    tampil["% Positif"] = tampil["% Positif"].map(lambda v: f"{v:.1f}%".replace(".", ","))
    st.table(tampil)
    tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Performa Algoritma
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    page_title("Perbandingan Performa Algoritma")
    perf = performa_semua()
    if perf.empty:
        st.info("Metrik performa belum tersedia pada fact_sentimen (data_uji).")
        return

    opsi_app = ["Semua aplikasi"] + sorted(perf["aplikasi"].unique())
    opsi_model = ["Semua algoritma"] + sorted(perf["model"].unique())

    mulai_kartu("Filter")
    c1, c2 = st.columns(2)
    with c1: f_app = st.selectbox("Aplikasi", opsi_app, key="fp_app")
    with c2: f_model = st.selectbox("Algoritma", opsi_model, key="fp_model")
    tutup_kartu()

    sub = perf.copy()
    if f_app != "Semua aplikasi":
        sub = sub[sub["aplikasi"] == f_app]
    if f_model != "Semua algoritma":
        sub = sub[sub["model"] == f_model]
    if sub.empty:
        st.warning("Tidak ada data performa untuk filter ini.")
        return

    terbaik_per_app = (
        perf.sort_values("macro_f1", ascending=False)
        .groupby("aplikasi").head(1).set_index("aplikasi")["model"].to_dict()
    )

    mulai_kartu("Tabel Perbandingan Metrik Evaluasi (data uji)")
    rows = []
    for _, r in sub.iterrows():
        bintang = " ★" if terbaik_per_app.get(r["aplikasi"]) == r["model"] else ""
        rows.append({
            "Aplikasi": r["aplikasi"],
            "Algoritma": f"{r['model']}{bintang}",
            "Accuracy": f"{r['accuracy']:.4f}".replace(".", ","),
            "Precision": f"{r['precision_pos']:.4f}".replace(".", ","),
            "Recall": f"{r['recall_pos']:.4f}".replace(".", ","),
            "F1": f"{r['f1_pos']:.4f}".replace(".", ","),
            "Macro-F1": f"{r['macro_f1']:.4f}".replace(".", ","),
            "Waktu latih (detik)": str(r["waktu_latih"]).replace(".", ",") if pd.notna(r["waktu_latih"]) else "-",
        })
    st.table(pd.DataFrame(rows))
    st.caption("Model terbaik ditandai ★ berdasarkan macro-F1; selisih kurang dari 0,01 dianggap setara. Precision, recall, dan F1 dihitung untuk kelas positif.")
    tutup_kartu()

    col_grafik, col_rek = st.columns([1.3, 1])
    with col_grafik:
        mulai_kartu("Grafik Macro-F1 per Aplikasi")
        fig = px.bar(
            perf, x="aplikasi", y="macro_f1", color="model",
            color_discrete_map={"Naive Bayes": "#A6C9E8", "SVM": HD_DARK,
                                "Complement Naive Bayes": "#A6C9E8",
                                "Naive Bayes (Complement)": "#A6C9E8",
                                "SVM (kernel linear)": HD_DARK},
            barmode="group",
            text=perf["macro_f1"].apply(lambda v: f"{v:.4f}".replace(".", ",")),
        )
        fig.update_traces(textposition="outside", textfont=dict(size=10))
        fig.update_layout(
            xaxis=dict(title="", tickfont=dict(size=12)),
            yaxis=dict(range=[0, 1.1], title="Macro-F1", tickfont=dict(size=11)),
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    with col_rek:
        mulai_kartu("Rekomendasi Algoritma")
        for app in sorted(perf["aplikasi"].unique()):
            sub_app = perf[perf["aplikasi"] == app].sort_values("macro_f1", ascending=False)
            if sub_app.empty: continue
            tb = sub_app.iloc[0]
            f1 = f"{tb['macro_f1']:.4f}".replace(".", ",")
            kedua = sub_app.iloc[1] if len(sub_app) > 1 else None
            f1k = f"{kedua['macro_f1']:.4f}".replace(".", ",") if kedua is not None else ""
            selisih = f"{(tb['macro_f1'] - kedua['macro_f1']):.4f}".replace(".", ",") if kedua is not None else ""
            warna = warna_aplikasi(app)
            st.markdown(
                f"""
                <div style="padding:0.7rem 0.9rem; margin-bottom:0.5rem; border-left:4px solid {warna}; background:#F8F5F3; border-radius:4px;">
                    <div style="color:{HD_DARK}; font-weight:700;">{app}: {tb['model']}</div>
                    <div style="color:#555; font-size:0.85rem;">macro-F1 {f1}{f' vs {f1k}' if kedua is not None else ''}{f', selisih {selisih}' if kedua is not None else ''}.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Admin
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    page_title("Halaman Admin")
    data = ringkasan_global()

    mulai_kartu("Unggah Data Ulasan Baru")
    st.caption("Unggah ulasan mentah hasil scraping (kolom wajib: content, score, at). Sistem memproses otomatis: preprocessing, pelabelan hybrid, dan prediksi dua model. Hanya ulasan yang tanggalnya setelah data terakhir aplikasi tersebut yang dimuat, maksimal 2.000 ulasan per unggahan.")
    c1, c2 = st.columns([1, 2])
    with c1: aplikasi = st.selectbox("Aplikasi target", data["aplikasi"], key="admin_app")
    with c2: berkas = st.file_uploader("Berkas ulasan (.csv atau .xlsx)", type=["csv", "xlsx"], key="admin_file")
    if st.button("Unggah dan proses", type="primary", disabled=berkas is None):
        proses_unggahan(user, aplikasi, berkas)
        ringkasan_global.clear()
        riwayat_unggahan.clear()
        st.rerun()
    tutup_kartu()

    mulai_kartu("Riwayat Unggahan")
    riwayat = riwayat_unggahan()
    if riwayat.empty:
        st.info("Belum ada unggahan.")
    else:
        tampil = pd.DataFrame({
            "ID": riwayat["id"].astype(int),
            "Waktu": riwayat["waktu"].apply(lambda t: t.strftime("%d %b %Y %H:%M") if pd.notna(t) else "-"),
            "Pengguna": riwayat["username"],
            "Aplikasi": riwayat["aplikasi"],
            "Berkas": riwayat["berkas"].fillna("-"),
            "Baris": riwayat["jumlah_baris"].fillna(0).astype(int),
            "Status": riwayat["status"],
            "Catatan": riwayat["catatan"].fillna("-"),
        })
        st.table(tampil)
    tutup_kartu()

    mulai_kartu("Kelola Pengguna")
    pengguna = daftar_pengguna()
    if not pengguna.empty:
        tampil = pengguna.rename(columns={"id": "ID", "username": "Username", "peran": "Peran"})
        st.table(tampil)
    tab1, tab2, tab3 = st.tabs(["Tambah akun", "Ubah password / peran", "Hapus akun"])
    with tab1:
        with st.form("tambah_akun_form", clear_on_submit=True):
            u = st.text_input("Username", key="tm_u")
            p = st.text_input("Password", type="password", key="tm_p")
            r = st.selectbox("Peran", ["Pengguna", "Admin"], key="tm_r")
            submit = st.form_submit_button("Tambah", type="primary")
        if submit:
            ok, pesan = tambah_akun(u, p, r)
            if ok:
                st.success(pesan)
                daftar_pengguna.clear()
                st.rerun()
            else: st.error(pesan)
    with tab2:
        if not pengguna.empty:
            pilih = st.selectbox("Pilih pengguna", pengguna["username"].tolist(), key="ub_pilih")
            with st.form("ubah_akun_form", clear_on_submit=True):
                p_baru = st.text_input("Password baru (kosongkan jika tidak diubah)", type="password", key="ub_p")
                r_baru = st.selectbox("Peran baru (kosongkan jika tidak diubah)", ["", "Pengguna", "Admin"], key="ub_r")
                submit = st.form_submit_button("Ubah", type="primary")
            if submit:
                id_user = int(pengguna[pengguna["username"] == pilih]["id"].iloc[0])
                ok, pesan = ubah_akun(id_user, p_baru, r_baru)
                if ok:
                    st.success(pesan)
                    daftar_pengguna.clear()
                    st.rerun()
                else: st.error(pesan)
    with tab3:
        if not pengguna.empty:
            lain = pengguna[pengguna["username"] != user["username"]]["username"].tolist()
            if lain:
                pilih = st.selectbox("Pilih pengguna yang akan dihapus", lain, key="hp_pilih")
                if st.button("Hapus akun", type="primary", key="hp_btn"):
                    id_user = int(pengguna[pengguna["username"] == pilih]["id"].iloc[0])
                    ok, pesan = hapus_akun(id_user)
                    if ok:
                        st.success(pesan)
                        daftar_pengguna.clear()
                        st.rerun()
                    else: st.error(pesan)
            else:
                st.info("Tidak ada pengguna lain untuk dihapus.")
    tutup_kartu()


def proses_unggahan(user: dict, aplikasi: str, berkas) -> None:
    try:
        if berkas.name.lower().endswith(".csv"):
            df = pd.read_csv(berkas)
        else:
            df = pd.read_excel(berkas)
    except Exception as exc:
        st.error(f"Berkas tidak dapat dibaca: {exc}"); return
    kolom = [c.lower() for c in df.columns]
    hilang = {"content", "score", "at"} - set(kolom)
    if hilang:
        st.error(f"Kolom wajib tidak lengkap: {', '.join(sorted(hilang))}."); return
    try:
        idm = model_utama_id()
        df_tgl = kueri(
            "SELECT MAX(w.tanggal) AS mx FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu "
            "JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi WHERE f.id_model = %s AND a.nama_aplikasi = %s",
            (idm, aplikasi),
        )
        tgl_terakhir = df_tgl.iloc[0]["mx"]
    except Exception:
        tgl_terakhir = None

    jumlah_awal = len(df)
    if tgl_terakhir is not None and "at" in [c.lower() for c in df.columns]:
        at_col = [c for c in df.columns if c.lower() == "at"][0]
        try:
            df["_tgl"] = pd.to_datetime(df[at_col], errors="coerce").dt.date
            df_baru = df[df["_tgl"] > tgl_terakhir]
            jumlah_baru = len(df_baru)
        except Exception:
            jumlah_baru = len(df)
    else:
        jumlah_baru = len(df)

    if jumlah_baru == 0:
        info_biru(f"Tidak ada ulasan yang lebih baru dari {tgl_terakhir}. {jumlah_awal} ulasan dilewati karena periodenya sudah tercakup.")
        try:
            eksekusi(
                "INSERT INTO riwayat_pelatihan (waktu, id_user, aplikasi, berkas, jumlah_baris, status, catatan) "
                "VALUES (NOW(), %s, %s, %s, %s, 'Tanpa data baru', %s)",
                (user["id_user"], aplikasi, berkas.name, 0,
                 f"{jumlah_awal} ulasan bertanggal sampai {tgl_terakhir} sudah ada; tidak ada ulasan yang lebih baru."),
            )
        except Exception: pass
        return

    if jumlah_baru > 2000:
        st.error(f"Jumlah baris baru ({jumlah_baru}) melebihi batas 2.000 ulasan per unggahan."); return
    try:
        eksekusi(
            "INSERT INTO riwayat_pelatihan (waktu, id_user, aplikasi, berkas, jumlah_baris, status, catatan) "
            "VALUES (NOW(), %s, %s, %s, %s, 'Diterima', %s)",
            (user["id_user"], aplikasi, berkas.name, jumlah_baru, "Menunggu pemrosesan pipeline"),
        )
        st.success(f"Berkas {berkas.name} diterima ({jumlah_baru} ulasan baru).")
    except Exception as exc:
        st.error(f"Gagal mencatat unggahan: {exc}")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def halaman_login() -> None:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-title">Dashboard Analisis Sentimen</div>'
        '<div class="login-subtitle">Instagram, TikTok, dan X (Google Play Store)</div>',
        unsafe_allow_html=True,
    )
    tab_masuk, tab_daftar = st.tabs(["Masuk", "Daftar"])
    with tab_masuk:
        with st.form("form_masuk", clear_on_submit=False):
            u = st.text_input("Username", key="masuk_u")
            p = st.text_input("Password", type="password", key="masuk_p")
            submit = st.form_submit_button("Masuk", use_container_width=True, type="primary")
        if submit:
            if not u or not p:
                st.error("Username dan password wajib diisi.")
            else:
                user = masuk(u, p)
                if user is None:
                    st.error("Username atau password salah.")
                else:
                    st.session_state["user"] = user
                    st.rerun()
    with tab_daftar:
        with st.form("form_daftar", clear_on_submit=True):
            u = st.text_input("Username baru", key="daftar_u")
            p = st.text_input("Password", type="password", key="daftar_p")
            k = st.text_input("Konfirmasi password", type="password", key="daftar_k")
            submit = st.form_submit_button("Daftar", use_container_width=True, type="primary")
        if submit:
            ok, pesan = daftar(u, p, k)
            if ok: st.success(pesan)
            else: st.error(pesan)
        st.caption("Akun baru otomatis berperan Pengguna.")
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
def aplikasi_utama() -> None:
    user = st.session_state["user"]
    opsi = ["Ringkasan", "Perbandingan Sentimen", "Performa Algoritma"]
    if user["role"] == "Admin":
        opsi.append("Admin")

    with st.sidebar:
        st.markdown('<div class="sidebar-brand">📊 Dashboard Analisis Sentimen</div>', unsafe_allow_html=True)
        aktif = st.session_state.get("halaman_aktif", "Ringkasan")
        if aktif not in opsi: aktif = "Ringkasan"
        pilihan = st.radio("Menu", opsi, index=opsi.index(aktif), key="nav_radio", label_visibility="collapsed")
        if pilihan != aktif:
            st.session_state["halaman_aktif"] = pilihan
            st.rerun()
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#6B7A8F; font-size:0.85rem; padding:0 0.4rem;'>Masuk sebagai "
                    f"<b>{user['username']}</b> ({user['role']})</div>", unsafe_allow_html=True)
        if st.button("Keluar", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()

    if pilihan == "Ringkasan": halaman_ringkasan()
    elif pilihan == "Perbandingan Sentimen": halaman_sentimen()
    elif pilihan == "Performa Algoritma": halaman_performa()
    elif pilihan == "Admin": halaman_admin(user)


def main() -> None:
    if "user" not in st.session_state: halaman_login()
    else: aplikasi_utama()


if __name__ == "__main__":
    main()
