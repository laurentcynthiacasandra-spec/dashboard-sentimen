"""Dashboard Analisis Sentimen Instagram, TikTok, dan X."""
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

# Palet warna modern
HD = "#1E5A8A"
HD_DARK = "#0A3B5E"
HD_LIGHT = "#E8F0F7"
ACCENT = "#F59E0B"
POS = "#10B981"
NEG = "#EF4444"
MUTED = "#64748B"
BG = "#F8FAFC"
CARD_BG = "#FFFFFF"
BORDER = "#E2E8F0"
IG_COLOR = "#8B5CF6"
TT_COLOR = "#14B8A6"
X_COLOR = "#1E3A5F"

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


# CSS modern
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"] * {
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    header, footer, #MainMenu {visibility: hidden;}
    .stApp {background: #F8FAFC;}
    .block-container {padding-top: 1.2rem !important; padding-bottom: 2.5rem; max-width: 1400px !important;}

    /* Sidebar modern */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] > div {padding-top: 1.2rem;}
    .sidebar-brand {
        display: flex; align-items: center; gap: 0.5rem;
        color: #1E5A8A; font-weight: 700; font-size: 1.05rem;
        padding: 0.4rem 0.6rem 1rem 0.6rem;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 0.8rem;
    }
    .sidebar-brand-icon {
        width: 32px; height: 32px; border-radius: 8px;
        background: linear-gradient(135deg, #1E5A8A 0%, #0A3B5E 100%);
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 1.1rem;
    }

    /* Sidebar nav vertical pill */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
        display: flex; flex-direction: column; gap: 3px; padding: 0;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background: transparent !important; border: none !important;
        padding: 0.65rem 1rem !important; border-radius: 8px !important;
        margin: 0 !important; cursor: pointer;
        font-weight: 500; font-size: 0.92rem;
        color: #334155 !important;
        transition: all 0.15s ease;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background: #F1F5F9 !important;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #1E5A8A 0%, #0A3B5E 100%) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(30,90,138,0.25);
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {display: none !important;}
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:last-child p {color: inherit !important; margin: 0;}

    /* Main radio pill */
    .main .stRadio > div[role="radiogroup"] {gap: 6px; flex-wrap: wrap; margin-bottom: 0.3rem;}
    .main .stRadio > div[role="radiogroup"] > label {
        background: #FFFFFF !important; border: 1px solid #E2E8F0 !important;
        padding: 0.45rem 1.2rem !important; border-radius: 24px !important;
        margin: 0 !important; cursor: pointer; font-weight: 500;
        color: #64748B !important; font-size: 0.88rem;
    }
    .main .stRadio > div[role="radiogroup"] > label:hover {
        background: #F1F5F9 !important; border-color: #CBD5E1 !important;
    }
    .main .stRadio > div[role="radiogroup"] > label:has(input:checked) {
        background: #1E5A8A !important; color: white !important; border-color: #1E5A8A !important;
    }
    .main .stRadio > div[role="radiogroup"] > label > div:first-child {display: none !important;}
    .main .stRadio > div[role="radiogroup"] > label > div:last-child p {color: inherit !important; margin: 0;}

    /* Judul halaman */
    .page-title {
        color: #0A3B5E; font-size: 1.75rem; font-weight: 700;
        margin: 0 0 0.3rem 0; letter-spacing: -0.02em;
    }
    .page-subtitle {
        color: #64748B; font-size: 0.95rem; margin-bottom: 1.2rem;
    }

    /* Kartu metrik kecil */
    .metrik-kecil {
        background: #FFFFFF; padding: 1rem 1.1rem;
        border-radius: 12px; border: 1px solid #E2E8F0;
        transition: all 0.2s ease;
        position: relative; overflow: hidden;
    }
    .metrik-kecil::before {
        content: ''; position: absolute; top: 0; left: 0;
        width: 100%; height: 3px;
        background: linear-gradient(90deg, #1E5A8A, #3B82F6);
    }
    .metrik-kecil:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transform: translateY(-1px);
    }
    .metrik-kecil-label {
        color: #64748B; font-size: 0.73rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.4px;
    }
    .metrik-kecil-nilai {
        font-size: 1.5rem; font-weight: 700; color: #0A3B5E;
        margin-top: 0.3rem; line-height: 1.1;
    }
    .metrik-kecil-sub {color: #94A3B8; font-size: 0.78rem; margin-top: 0.2rem;}

    /* Kartu per aplikasi */
    .kartu-app {
        background: #FFFFFF; padding: 1.3rem;
        border-radius: 12px; border: 1px solid #E2E8F0;
        transition: all 0.2s ease; min-height: 240px;
        position: relative; overflow: hidden;
    }
    .kartu-app::before {
        content: ''; position: absolute; top: 0; left: 0;
        width: 4px; height: 100%;
    }
    .kartu-app.ig::before {background: #8B5CF6;}
    .kartu-app.tt::before {background: #14B8A6;}
    .kartu-app.x::before {background: #1E3A5F;}
    .kartu-app:hover {box-shadow: 0 6px 20px rgba(0,0,0,0.06); transform: translateY(-2px);}
    .kartu-app-nama {font-size: 1.4rem; font-weight: 700; margin: 0;}
    .kartu-app-pct {font-size: 2.6rem; font-weight: 800; margin: 0.9rem 0 0.1rem 0; line-height: 1; letter-spacing: -0.02em;}
    .kartu-app-pos {color: #64748B; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.8rem;}
    .mini-bar {display: flex; width: 100%; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 0.7rem; background: #F1F5F9;}
    .kartu-app-stat {color: #64748B; font-size: 0.8rem; line-height: 1.5;}

    /* Kartu umum */
    .kartu {
        background: #FFFFFF; padding: 1.3rem;
        border-radius: 12px; border: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    .kartu-judul {
        color: #0A3B5E; font-weight: 700; font-size: 1.05rem;
        margin-bottom: 1rem; letter-spacing: -0.01em;
    }

    /* Insight bullets */
    .insight {display: flex; gap: 0.7rem; padding: 0.4rem 0; align-items: flex-start;}
    .insight-dot {
        width: 8px; height: 8px; border-radius: 50%;
        background: linear-gradient(135deg, #1E5A8A, #3B82F6);
        margin-top: 0.5rem; flex-shrink: 0;
    }
    .insight-text {font-size: 0.93rem; color: #334155; line-height: 1.6;}

    /* Banner insight kuning */
    .banner-insight {
        background: linear-gradient(135deg, #FEF9E7 0%, #FFF4D0 100%);
        border: 1px solid #FDE68A;
        color: #78350F; padding: 1rem 1.2rem;
        border-radius: 10px; margin: 1rem 0;
        font-size: 0.93rem;
    }
    .banner-insight b {color: #0A3B5E;}

    /* Info box biru */
    .info-biru {
        background: #EFF6FF; border: 1px solid #BFDBFE;
        color: #1E40AF; padding: 0.9rem 1.1rem;
        border-radius: 10px; margin: 1rem 0; font-size: 0.92rem;
    }

    /* Login modern — gradient bg, kartu floating */
    .login-wrapper {
        min-height: calc(100vh - 80px);
        display: flex; align-items: center; justify-content: center;
        padding: 2rem 1rem;
    }
    .login-card {
        background: #FFFFFF; padding: 2.5rem 2.2rem; border-radius: 20px;
        box-shadow: 0 20px 50px rgba(30,90,138,0.12);
        max-width: 440px; width: 100%; margin: 0 auto;
        border: 1px solid #E2E8F0;
    }
    .login-logo {
        width: 60px; height: 60px; border-radius: 16px;
        background: linear-gradient(135deg, #1E5A8A 0%, #0A3B5E 100%);
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 1.8rem;
        margin: 0 auto 1rem auto;
        box-shadow: 0 8px 20px rgba(30,90,138,0.25);
    }
    .login-title {
        color: #0A3B5E; text-align: center; font-size: 1.7rem;
        font-weight: 800; margin: 0 0 0.4rem 0; letter-spacing: -0.02em;
    }
    .login-subtitle {
        color: #64748B; text-align: center; font-size: 0.92rem;
        margin-bottom: 1.6rem;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px; font-weight: 600; font-size: 0.9rem;
        transition: all 0.15s ease;
    }
    .stButton > button[kind="primary"],
    .stForm button[kind="primaryFormSubmit"] {
        background: linear-gradient(135deg, #1E5A8A 0%, #0A3B5E 100%) !important;
        border: none !important; color: white !important;
        box-shadow: 0 2px 8px rgba(30,90,138,0.2);
    }
    .stButton > button[kind="primary"]:hover,
    .stForm button[kind="primaryFormSubmit"]:hover {
        background: linear-gradient(135deg, #0A3B5E 0%, #062843 100%) !important;
        box-shadow: 0 4px 14px rgba(30,90,138,0.3);
        transform: translateY(-1px);
    }

    /* Input & selectbox modern */
    .stTextInput input, .stSelectbox > div > div, .stDateInput input {
        border-radius: 8px !important;
        border: 1px solid #E2E8F0 !important;
        font-size: 0.9rem;
    }
    .stTextInput input:focus {
        border-color: #1E5A8A !important;
        box-shadow: 0 0 0 3px rgba(30,90,138,0.1) !important;
    }

    /* Tabel st.table */
    .stTable thead tr th {
        background: #F1F5F9; color: #0A3B5E;
        font-weight: 700; font-size: 0.82rem;
        text-transform: uppercase; letter-spacing: 0.3px;
    }
    .stTable tbody tr td {font-size: 0.88rem; color: #334155;}

    /* Streamlit tabs (login) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem; border-bottom: 1px solid #E2E8F0;
        padding: 0;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent; border: none;
        padding: 0.6rem 0; color: #64748B;
        font-weight: 600; font-size: 0.95rem;
    }
    .stTabs [aria-selected="true"] {
        color: #1E5A8A !important;
        border-bottom: 2px solid #1E5A8A !important;
    }

    /* Hilangkan default label jarak */
    .stSelectbox label, .stDateInput label, .stTextInput label,
    .stRadio > label, .stFileUploader label {
        font-weight: 500; color: #475569; font-size: 0.85rem;
    }
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
    """Jumlah ulasan per bulan per aplikasi per sentimen."""
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
               DATE_TRUNC('month', w.tanggal)::date AS bulan,
               s.label_sentimen AS label,
               COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        JOIN dim_waktu w ON w.id_waktu = f.id_waktu
        WHERE f.id_model = %s {wh}
        GROUP BY a.nama_aplikasi, DATE_TRUNC('month', w.tanggal), s.label_sentimen
        ORDER BY DATE_TRUNC('month', w.tanggal)
    """
    df = kueri(sql, tuple(parm))
    if not df.empty:
        df["label"] = df["label"].str.strip().str.title()
    return df


@st.cache_data(ttl=300, show_spinner=False)
def sentimen_tersaring(aplikasi: str, dari, sampai, tahun) -> pd.DataFrame:
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
def page_title(judul: str, subjudul: str = "") -> None:
    st.markdown(f'<div class="page-title">{judul}</div>', unsafe_allow_html=True)
    if subjudul:
        st.markdown(f'<div class="page-subtitle">{subjudul}</div>', unsafe_allow_html=True)


def metrik_kecil(label: str, nilai: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="metrik-kecil">'
        f'<div class="metrik-kecil-label">{label}</div>'
        f'<div class="metrik-kecil-nilai">{nilai}</div>'
        f'<div class="metrik-kecil-sub">{sub or "&nbsp;"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def kartu_aplikasi(nama: str, positif: int, negatif: int, total: int) -> None:
    pct = (positif / total * 100) if total else 0
    warna = warna_aplikasi(nama)
    pct_str = f"{pct:.1f}%".replace(".", ",")
    pos_str = f"{positif:,}".replace(",", ".")
    neg_str = f"{negatif:,}".replace(",", ".")
    tot_str = f"{total:,}".replace(",", ".")
    klass = "ig" if "insta" in nama.lower() else ("tt" if "tik" in nama.lower() else "x")
    st.markdown(
        f'<div class="kartu-app {klass}">'
        f'<div class="kartu-app-nama" style="color:{warna};">{nama}</div>'
        f'<div class="kartu-app-pct" style="color:{HD_DARK};">{pct_str}</div>'
        f'<div class="kartu-app-pos">positif</div>'
        f'<div class="mini-bar">'
        f'<div style="width:{pct}%; background:{POS};"></div>'
        f'<div style="width:{100-pct}%; background:{NEG};"></div>'
        f'</div>'
        f'<div class="kartu-app-stat">'
        f'{pos_str} positif · {neg_str} negatif · {tot_str} ulasan'
        f'</div></div>',
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
    page_title("Ringkasan Insight Utama", "Pantauan sentimen pengguna aplikasi media sosial")
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
            textposition="outside", textfont=dict(size=12, color=HD_DARK, family="Inter"),
        ))
        fig.update_layout(
            xaxis=dict(range=[0, 100], title="% positif", showgrid=True, gridcolor="#F1F5F9"),
            yaxis=dict(title="", tickfont=dict(size=13, family="Inter")),
            height=280, margin=dict(l=10, r=40, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        tutup_kartu()

    with col_pie:
        mulai_kartu("Distribusi Sentimen Keseluruhan")
        pos_total = int(rincian[rincian["label"] == "Positif"]["jumlah"].sum())
        neg_total = int(rincian[rincian["label"] == "Negatif"]["jumlah"].sum())
        fig = go.Figure(data=[go.Pie(
            labels=[f"Positif ({pos_total:,})".replace(",", "."),
                    f"Negatif ({neg_total:,})".replace(",", ".")],
            values=[pos_total, neg_total],
            marker=dict(colors=[POS, NEG], line=dict(color="white", width=3)),
            hole=0.6, textinfo="none",
        )])
        fig.update_layout(
            margin=dict(l=20, r=20, t=10, b=30), height=280,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font=dict(size=12, family="Inter")),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
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
    page_title("Perbandingan Sentimen", "Analisis proporsi sentimen antar aplikasi dan selang waktu")
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
        sumber = st.selectbox("Sumber label", ["Hasil pelabelan (semua ulasan)"], key="fs_sumber")
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
            xaxis=dict(title="", tickfont=dict(size=13, family="Inter")),
            yaxis=dict(title="", range=[0, 100], ticksuffix="%", tickfont=dict(size=11, family="Inter"),
                       showgrid=True, gridcolor="#F1F5F9"),
            height=380, margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
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
                    name=app, legendgroup=app,
                    line=dict(color=warna, width=2.8, shape="spline", smoothing=0.8),
                    marker=dict(size=8, color=warna, line=dict(color="white", width=1.5)),
                    hovertemplate=f"<b>{app}</b> · Positif<br>%{{x|%b %Y}}<br>%{{y:,}} ulasan<extra></extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=neg_s["bulan"], y=neg_s["jumlah"], mode="lines+markers",
                    name=app, legendgroup=app, showlegend=False,
                    line=dict(color=warna, width=2.2, dash="dash", shape="spline", smoothing=0.8),
                    marker=dict(size=8, color="white", line=dict(color=warna, width=2)),
                    hovertemplate=f"<b>{app}</b> · Negatif<br>%{{x|%b %Y}}<br>%{{y:,}} ulasan<extra></extra>",
                ))
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=10, color="#334155", line=dict(color="white", width=1.5)),
                name="Positif", legendgroup="legend_sym",
            ))
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="markers",
                marker=dict(size=10, color="white", line=dict(color="#334155", width=2)),
                name="Negatif", legendgroup="legend_sym",
            ))
            fig.update_layout(
                xaxis=dict(
                    title="",
                    tickfont=dict(size=10, family="Inter", color="#475569"),
                    showgrid=True, gridcolor="#F1F5F9",
                    tickformat="%b %Y",
                    dtick="M1",
                    tickangle=-45,
                    showline=True, linecolor="#CBD5E1",
                ),
                yaxis=dict(title="", tickfont=dict(size=11, family="Inter", color="#475569"), showgrid=True, gridcolor="#F1F5F9",
                           tickformat=",d", separatethousands=True),
                height=460, margin=dict(l=10, r=10, t=10, b=150),
                legend=dict(orientation="h", yanchor="bottom", y=-0.48, xanchor="center", x=0.5, font=dict(size=11, family="Inter")),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
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
def render_cm_mini(tp, fn, fp, tn, judul, acc):
    total = tp + fn + fp + tn
    pct_tp = (tp / total * 100) if total else 0.0
    pct_fn = (fn / total * 100) if total else 0.0
    pct_fp = (fp / total * 100) if total else 0.0
    pct_tn = (tn / total * 100) if total else 0.0
    acc_s = f"{acc:.2f}%".replace(".", ",")
    tp_s = f"{tp:,}".replace(",", ".")
    fn_s = f"{fn:,}".replace(",", ".")
    fp_s = f"{fp:,}".replace(",", ".")
    tn_s = f"{tn:,}".replace(",", ".")
    total_s = f"{total:,}".replace(",", ".")
    pct_tp_s = f"{pct_tp:.1f}%".replace(".", ",")
    pct_fn_s = f"{pct_fn:.1f}%".replace(".", ",")
    pct_fp_s = f"{pct_fp:.1f}%".replace(".", ",")
    pct_tn_s = f"{pct_tn:.1f}%".replace(".", ",")
    cell_benar = "background:linear-gradient(135deg,#10B981,#059669); color:white;"
    cell_salah = "background:linear-gradient(135deg,#1E5A8A,#0A3B5E); color:white;"
    html = (
        f'<div style="background:white; border:1px solid #E2E8F0; border-radius:10px; padding:0.9rem 1rem; margin-bottom:0.7rem;">'
        f'<div style="color:#0A3B5E; font-weight:700; font-size:0.9rem;">{judul}</div>'
        f'<div style="color:#64748B; font-size:0.74rem; margin-bottom:0.6rem;">Akurasi {acc_s} · total {total_s}</div>'
        '<table style="width:100%; border-collapse:separate; border-spacing:3px; font-family:Inter;">'
        '<tr>'
        '<td style="width:60px;"></td>'
        '<td colspan="2" style="text-align:center; font-size:0.65rem; color:#64748B; text-transform:uppercase; letter-spacing:0.4px; padding-bottom:0.2rem; font-weight:600;">Prediksi</td>'
        '</tr>'
        '<tr>'
        '<td></td>'
        '<td style="text-align:center; font-size:0.72rem; color:#0A3B5E; font-weight:600; padding:0.15rem;">Positif</td>'
        '<td style="text-align:center; font-size:0.72rem; color:#0A3B5E; font-weight:600; padding:0.15rem;">Negatif</td>'
        '</tr>'
        '<tr>'
        '<td style="text-align:right; font-size:0.7rem; color:#0A3B5E; font-weight:600; padding-right:0.4rem;">Aktual<br>Positif</td>'
        f'<td style="{cell_benar} text-align:center; padding:0.55rem 0.3rem; border-radius:6px;">'
        f'<div style="font-size:1rem; font-weight:700; line-height:1;">{tp_s}</div>'
        f'<div style="font-size:0.62rem; opacity:0.9; margin-top:0.15rem;">TP · {pct_tp_s}</div></td>'
        f'<td style="{cell_salah} text-align:center; padding:0.55rem 0.3rem; border-radius:6px;">'
        f'<div style="font-size:1rem; font-weight:700; line-height:1;">{fn_s}</div>'
        f'<div style="font-size:0.62rem; opacity:0.9; margin-top:0.15rem;">FN · {pct_fn_s}</div></td>'
        '</tr>'
        '<tr>'
        '<td style="text-align:right; font-size:0.7rem; color:#0A3B5E; font-weight:600; padding-right:0.4rem;">Aktual<br>Negatif</td>'
        f'<td style="{cell_salah} text-align:center; padding:0.55rem 0.3rem; border-radius:6px;">'
        f'<div style="font-size:1rem; font-weight:700; line-height:1;">{fp_s}</div>'
        f'<div style="font-size:0.62rem; opacity:0.9; margin-top:0.15rem;">FP · {pct_fp_s}</div></td>'
        f'<td style="{cell_benar} text-align:center; padding:0.55rem 0.3rem; border-radius:6px;">'
        f'<div style="font-size:1rem; font-weight:700; line-height:1;">{tn_s}</div>'
        f'<div style="font-size:0.62rem; opacity:0.9; margin-top:0.15rem;">TN · {pct_tn_s}</div></td>'
        '</tr>'
        '</table></div>'
    )
    return html


def _th_cell(label):
    return f'<th style="padding:0.6rem 0.8rem; text-align:right; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.3px; color:#0A3B5E;">{label}</th>'


def tampilkan_performa_app(app: str, perf: pd.DataFrame, df_metrik: pd.DataFrame) -> None:
    sub = perf[perf["aplikasi"] == app].copy()
    if sub.empty:
        st.info(f"Tidak ada data performa untuk {app}.")
        return
    model_terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]["model"]

    # Tabel metrik
    mulai_kartu(f"Metrik Evaluasi — {app}")
    header = (
        '<tr style="background:#F1F5F9;">'
        '<th style="padding:0.6rem 0.8rem; text-align:left; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.3px; color:#0A3B5E;">Algoritma</th>'
        + _th_cell("Accuracy") + _th_cell("Precision") + _th_cell("Recall")
        + _th_cell("F1") + _th_cell("Macro-F1") + _th_cell("Waktu (dtk)")
        + '</tr>'
    )
    baris = []
    for _, r in sub.iterrows():
        terbaik = r["model"] == model_terbaik
        bg = "#ECFDF5" if terbaik else "transparent"
        warna = "#064E3B" if terbaik else "#334155"
        tebal = "font-weight:600;" if terbaik else ""
        bintang = ' <span style="color:#F59E0B; font-size:1rem;">★</span>' if terbaik else ""
        acc_s = ("%.4f" % r["accuracy"]).replace(".", ",")
        prec_s = ("%.4f" % r["precision_pos"]).replace(".", ",")
        rec_s = ("%.4f" % r["recall_pos"]).replace(".", ",")
        f1_s = ("%.4f" % r["f1_pos"]).replace(".", ",")
        mf1_s = ("%.4f" % r["macro_f1"]).replace(".", ",")
        wl_s = str(r["waktu_latih"]).replace(".", ",") if pd.notna(r["waktu_latih"]) else "-"
        baris.append(
            f'<tr style="background:{bg}; color:{warna}; {tebal}">'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0;">{r["model"]}{bintang}</td>'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0; text-align:right;">{acc_s}</td>'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0; text-align:right;">{prec_s}</td>'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0; text-align:right;">{rec_s}</td>'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0; text-align:right;">{f1_s}</td>'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0; text-align:right;">{mf1_s}</td>'
            f'<td style="padding:0.6rem 0.8rem; border-top:1px solid #E2E8F0; text-align:right;">{wl_s}</td>'
            '</tr>'
        )
    st.markdown(
        '<table style="width:100%; border-collapse:collapse; font-size:0.85rem; font-family:Inter;">'
        f'<thead>{header}</thead><tbody>{"".join(baris)}</tbody></table>',
        unsafe_allow_html=True,
    )
    tutup_kartu()

    # Confusion matrix 2 model side by side (ukuran kecil)
    mulai_kartu(f"Confusion Matrix — {app}")
    sub_met = df_metrik[df_metrik["aplikasi"] == app]
    model_list = sorted(sub_met["model"].unique())
    cols = st.columns([1, 1, 0.3])
    for idx, model_nama in enumerate(model_list[:2]):
        sub_mm = sub_met[sub_met["model"] == model_nama]
        cm = {(a, p): int(n) for a, p, n in zip(sub_mm["aktual"], sub_mm["prediksi"], sub_mm["n"])}
        tp = cm.get(("Positif", "Positif"), 0); fn = cm.get(("Positif", "Negatif"), 0)
        fp = cm.get(("Negatif", "Positif"), 0); tn = cm.get(("Negatif", "Negatif"), 0)
        total = tp + fn + fp + tn
        acc = ((tp + tn) / total * 100) if total else 0.0
        with cols[idx]:
            st.markdown(render_cm_mini(tp, fn, fp, tn, model_nama, acc), unsafe_allow_html=True)
    st.caption("Sel hijau: prediksi benar (TP/TN). Sel biru: prediksi salah (FN/FP).")
    tutup_kartu()

    # Grafik macro-F1 khusus aplikasi ini
    mulai_kartu(f"Perbandingan Macro-F1 — {app}")
    fig = go.Figure()
    for _, r in sub.iterrows():
        warna_bar = HD_DARK if "svm" in r["model"].lower() else "#93C5FD"
        label = f"{r['macro_f1']:.4f}".replace(".", ",")
        fig.add_trace(go.Bar(
            x=[r["model"]], y=[r["macro_f1"]],
            marker_color=warna_bar, text=label, textposition="outside",
            textfont=dict(size=12, family="Inter", color="#0A3B5E"),
            showlegend=False,
        ))
    fig.update_layout(
        xaxis=dict(title="", tickfont=dict(size=12, family="Inter")),
        yaxis=dict(range=[0, 1.1], title="Macro-F1", tickfont=dict(size=11, family="Inter"),
                   showgrid=True, gridcolor="#F1F5F9"),
        height=280, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    tutup_kartu()

    # Rekomendasi
    tb = sub.sort_values("macro_f1", ascending=False).iloc[0]
    f1 = f"{tb['macro_f1']:.4f}".replace(".", ",")
    kedua = sub.sort_values("macro_f1", ascending=False).iloc[1] if len(sub) > 1 else None
    f1k = f"{kedua['macro_f1']:.4f}".replace(".", ",") if kedua is not None else ""
    selisih_v = (tb['macro_f1'] - kedua['macro_f1']) if kedua is not None else 0
    selisih_s = f"{selisih_v:.4f}".replace(".", ",") if kedua is not None else ""
    warna = warna_aplikasi(app)
    tambahan = (f" (selisih {selisih_s} vs {kedua['model']} {f1k})" if kedua is not None else "")
    st.markdown(
        f'<div style="padding:1rem 1.2rem; margin-top:0.5rem; border-left:4px solid {warna}; background:#F8FAFC; border-radius:8px;">'
        f'<div style="color:#64748B; font-size:0.78rem; text-transform:uppercase; letter-spacing:0.5px; font-weight:600;">Rekomendasi Algoritma</div>'
        f'<div style="color:{HD_DARK}; font-weight:700; font-size:1.15rem; margin:0.3rem 0;">{tb["model"]} · macro-F1 {f1}</div>'
        f'<div style="color:#64748B; font-size:0.85rem;">Model terbaik untuk {app}{tambahan}.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def halaman_performa() -> None:
    page_title("Perbandingan Performa Algoritma", "Evaluasi Naive Bayes dan SVM per aplikasi")
    perf = performa_semua()
    df_metrik = metrik_model()
    if perf.empty or df_metrik.empty:
        st.info("Metrik performa belum tersedia pada fact_sentimen (data_uji).")
        return

    aplikasi_list = sorted(perf["aplikasi"].unique())
    tabs = st.tabs(aplikasi_list)
    for tab, app in zip(tabs, aplikasi_list):
        with tab:
            tampilkan_performa_app(app, perf, df_metrik)


# ---------------------------------------------------------------------------
# Halaman: Admin
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    page_title("Halaman Admin", "Unggah data ulasan baru dan kelola pengguna")
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
                st.success(pesan); daftar_pengguna.clear(); st.rerun()
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
                    st.success(pesan); daftar_pengguna.clear(); st.rerun()
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
                        st.success(pesan); daftar_pengguna.clear(); st.rerun()
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
# Login modern
# ---------------------------------------------------------------------------
def halaman_login() -> None:
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-logo">📊</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-title">Dashboard Analisis Sentimen</div>'
        '<div class="login-subtitle">Instagram, TikTok, dan X &middot; Google Play Store</div>',
        unsafe_allow_html=True,
    )
    tab_masuk, tab_daftar = st.tabs(["Masuk", "Daftar"])
    with tab_masuk:
        with st.form("form_masuk", clear_on_submit=False):
            u = st.text_input("Username", key="masuk_u", placeholder="masukkan username")
            p = st.text_input("Password", type="password", key="masuk_p", placeholder="masukkan password")
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
            u = st.text_input("Username baru", key="daftar_u", placeholder="pilih username unik")
            p = st.text_input("Password", type="password", key="daftar_p", placeholder="minimal 6 karakter")
            k = st.text_input("Konfirmasi password", type="password", key="daftar_k", placeholder="ulangi password")
            submit = st.form_submit_button("Daftar", use_container_width=True, type="primary")
        if submit:
            ok, pesan = daftar(u, p, k)
            if ok: st.success(pesan)
            else: st.error(pesan)
        st.caption("Akun baru otomatis berperan Pengguna.")
    st.markdown('</div></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
def aplikasi_utama() -> None:
    user = st.session_state["user"]
    opsi = ["Ringkasan", "Perbandingan Sentimen", "Performa Algoritma"]
    if user["role"] == "Admin":
        opsi.append("Admin")

    with st.sidebar:
        st.markdown(
            '<div class="sidebar-brand">'
            '<div class="sidebar-brand-icon">📊</div>'
            '<div>Analisis Sentimen</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        aktif = st.session_state.get("halaman_aktif", "Ringkasan")
        if aktif not in opsi: aktif = "Ringkasan"
        pilihan = st.radio("Menu", opsi, index=opsi.index(aktif), key="nav_radio", label_visibility="collapsed")
        if pilihan != aktif:
            st.session_state["halaman_aktif"] = pilihan
            st.rerun()
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:#64748B; font-size:0.82rem; padding:0 0.6rem 0.4rem 0.6rem;">Masuk sebagai</div>'
            f'<div style="color:#0A3B5E; font-weight:700; font-size:0.95rem; padding:0 0.6rem 0.2rem 0.6rem;">{user["username"]}</div>'
            f'<div style="color:#64748B; font-size:0.78rem; padding:0 0.6rem 0.8rem 0.6rem;">Peran: {user["role"]}</div>',
            unsafe_allow_html=True,
        )
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
