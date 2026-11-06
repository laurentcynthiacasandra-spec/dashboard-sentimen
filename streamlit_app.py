"""Dashboard Analisis Sentimen Instagram, TikTok, dan X.

Layout sidebar nav + 3 kartu per aplikasi + bar chart + donut.
"""
import os

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

    /* Vertical radio nav di sidebar */
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] {
        display: flex; flex-direction: column; gap: 4px; padding: 0;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background: transparent !important; border: none !important;
        padding: 0.6rem 0.9rem !important; border-radius: 6px !important;
        margin: 0 !important; cursor: pointer; font-weight: 500;
        color: #333 !important;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
        background: #F4F0EE !important;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) {
        background: #175A85 !important; color: white !important;
    }
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {display: none !important;}
    [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:last-child p {color: inherit !important; margin: 0;}

    /* Radio di MAIN area tetap pill horizontal */
    .main .stRadio > div[role="radiogroup"] {
        gap: 6px; flex-wrap: wrap; margin-bottom: 0.3rem;
    }
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

    .page-title {
        color: #0F3F5E; font-size: 1.7rem; font-weight: 700;
        margin: 0 0 1rem 0;
    }

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
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        min-height: 230px;
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

    .login-card {
        background: #FFFFFF; padding: 1.8rem 1.6rem; border-radius: 12px;
        border: 1px solid #E5DED9; box-shadow: 0 6px 24px rgba(0,0,0,0.08);
        max-width: 400px; margin: 3rem auto;
    }
    .login-title {color: #175A85; text-align: center; font-size: 1.5rem; font-weight: 700; margin: 0;}
    .login-subtitle {color: #6B7A8F; text-align: center; font-size: 0.88rem; margin-bottom: 1.2rem;}

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
    .stTable tbody tr td {font-size: 0.88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Koneksi basis data
# ---------------------------------------------------------------------------
def _get_dsn() -> str:
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.environ["DATABASE_URL"]


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
                cur.execute("SELECT 1")
                cur.fetchone()
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


# ---------------------------------------------------------------------------
# Kueri data
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def model_utama_id() -> int:
    df = kueri(
        "SELECT id_model FROM dim_model WHERE COALESCE(pembanding, FALSE) = FALSE ORDER BY id_model LIMIT 1"
    )
    if not df.empty: return int(df.iloc[0]["id_model"])
    df2 = kueri("SELECT MIN(id_model) AS id_min FROM fact_sentimen")
    return int(df2.iloc[0]["id_min"]) if not df2.empty else 1


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
    tgl = kueri(
        "SELECT MAX(w.tanggal) AS mx FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu"
    ).iloc[0]["mx"]
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
    return pd.DataFrame(baris)


@st.cache_data(ttl=300, show_spinner=False)
def rentang_tanggal(aplikasi: str) -> tuple:
    idm = model_utama_id()
    if aplikasi == "Semua":
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
def sentimen_tersaring(aplikasi: str, dari, sampai) -> pd.DataFrame:
    idm = model_utama_id()
    cond = "" if aplikasi == "Semua" else "AND a.nama_aplikasi = %s"
    parm = () if aplikasi == "Semua" else (aplikasi,)
    if dari and sampai:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi, s.label_sentimen AS label, COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE f.id_model = %s AND w.tanggal BETWEEN %s AND %s {cond}
            GROUP BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, (idm, dari, sampai) + parm)
    else:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi, s.label_sentimen AS label, COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            WHERE f.id_model = %s {cond}
            GROUP BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, (idm,) + parm)
    if not df.empty:
        df["label"] = df["label"].str.strip().str.title()
    return df


@st.cache_data(ttl=60, show_spinner=False)
def riwayat_unggahan() -> pd.DataFrame:
    try:
        return kueri(
            """
            SELECT r.id, r.waktu, u.username, r.aplikasi, r.berkas,
                   r.jumlah_baris, r.status, r.catatan
            FROM riwayat_pelatihan r JOIN users u ON u.id_user = r.id_user
            ORDER BY r.waktu DESC LIMIT 50
            """
        )
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


# ---------------------------------------------------------------------------
# Halaman: Ringkasan
# ---------------------------------------------------------------------------
def halaman_ringkasan() -> None:
    page_title("Ringkasan Insight Utama")
    data = ringkasan_global()
    tgl_str = data["tanggal_terbaru"].strftime("%Y-%m-%d") if pd.notna(data["tanggal_terbaru"]) else "-"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metrik_kecil("TOTAL ULASAN DIANALISIS",
                     f"{data['total']:,}".replace(",", "."),
                     f"{data['jumlah_aplikasi']} aplikasi")
    with k2:
        metrik_kecil("RATA-RATA SENTIMEN POSITIF",
                     f"{data['positif_pct']:.1f}%".replace(".", ","),
                     "dari seluruh ulasan")
    with k3:
        metrik_kecil("MODEL TERBAIK", "SVM", "berdasarkan macro-F1")
    with k4:
        metrik_kecil("DATA TERAKHIR", tgl_str, "tanggal ulasan terbaru")

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    rincian = data["rincian"]
    cols = st.columns(len(data["aplikasi"]))
    for i, app in enumerate(data["aplikasi"]):
        sub = rincian[rincian["aplikasi"] == app]
        positif = int(sub[sub["label"] == "Positif"]["jumlah"].sum())
        negatif = int(sub[sub["label"] == "Negatif"]["jumlah"].sum())
        total = int(sub["total_app"].max()) if not sub.empty else (positif + negatif)
        with cols[i]:
            kartu_aplikasi(app, positif, negatif, total)

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
            xaxis=dict(range=[0, 100], title="", showgrid=True, gridcolor="#eee",
                       ticksuffix="%", tickfont=dict(size=11)),
            yaxis=dict(title="", tickfont=dict(size=13)),
            height=280, margin=dict(l=10, r=40, t=10, b=10),
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
            hovertemplate="%{label}<br>%{value:,}<extra></extra>",
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
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        aplikasi = st.radio("Aplikasi", ["Semua"] + data["aplikasi"], horizontal=True,
                            key="fs_app", label_visibility="collapsed")
    mn, mx = rentang_tanggal(aplikasi)
    with c2:
        dari = st.date_input("Dari", value=None, min_value=mn, max_value=mx,
                             key="fs_dari", format="DD/MM/YYYY")
    with c3:
        sampai = st.date_input("Sampai", value=None, min_value=mn, max_value=mx,
                               key="fs_sampai", format="DD/MM/YYYY")
    if mn and mx:
        st.caption(f"Data tersedia: {mn.strftime('%d/%m/%Y')} s.d. {mx.strftime('%d/%m/%Y')}")
    tutup_kartu()

    if dari and sampai and dari > sampai:
        st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'.")
        return
    df = sentimen_tersaring(aplikasi, dari, sampai)
    if df.empty:
        st.warning("Tidak ada ulasan pada selang waktu ini.")
        return
    pivot = df.pivot(index="aplikasi", columns="label", values="jumlah").fillna(0)
    for k in ["Positif", "Negatif"]:
        if k not in pivot.columns: pivot[k] = 0
    pivot["Total"] = pivot["Positif"] + pivot["Negatif"]
    pivot["Pos_pct"] = (pivot["Positif"] / pivot["Total"] * 100).round(1)
    pivot["Neg_pct"] = (pivot["Negatif"] / pivot["Total"] * 100).round(1)
    pivot = pivot.reset_index()

    col_chart, col_tabel = st.columns([1.3, 1])
    with col_chart:
        mulai_kartu("Perbandingan Proporsi Sentimen Positif vs Negatif")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Positif", x=pivot["aplikasi"], y=pivot["Pos_pct"], marker_color=POS,
            text=pivot["Pos_pct"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
            textposition="inside", textfont=dict(color="white", size=13),
        ))
        fig.add_trace(go.Bar(
            name="Negatif", x=pivot["aplikasi"], y=pivot["Neg_pct"], marker_color=NEG,
            text=pivot["Neg_pct"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
            textposition="inside", textfont=dict(color="white", size=13),
        ))
        fig.update_layout(
            barmode="stack",
            xaxis=dict(title="", tickfont=dict(size=13)),
            yaxis=dict(title="", range=[0, 100], ticksuffix="%", tickfont=dict(size=11),
                       showgrid=True, gridcolor="#eee"),
            height=360, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    with col_tabel:
        mulai_kartu("Tabel Perbandingan")
        tampil = pivot[["aplikasi", "Positif", "Negatif", "Pos_pct"]].copy()
        tampil.columns = ["Aplikasi", "Positif", "Negatif", "% Positif"]
        tampil["Positif"] = tampil["Positif"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
        tampil["Negatif"] = tampil["Negatif"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
        tampil["% Positif"] = tampil["% Positif"].map(lambda v: f"{v:.1f}%".replace(".", ","))
        st.table(tampil)
        tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Performa Algoritma
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    page_title("Perbandingan Performa Algoritma")
    data = ringkasan_global()
    mulai_kartu("Filter Aplikasi")
    aplikasi = st.radio("Aplikasi", data["aplikasi"], horizontal=True,
                        key="fp_app", label_visibility="collapsed")
    tutup_kartu()

    perf = performa_semua()
    if perf.empty:
        st.info("Metrik performa belum tersedia.")
        return
    sub = perf[perf["aplikasi"] == aplikasi].sort_values("model")
    if sub.empty:
        st.warning(f"Tidak ada data performa untuk aplikasi {aplikasi}.")
        return
    terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]

    mulai_kartu("Rekomendasi Algoritma per Aplikasi")
    cols = st.columns(len(data["aplikasi"]))
    for i, app in enumerate(data["aplikasi"]):
        sub_app = perf[perf["aplikasi"] == app].sort_values("macro_f1", ascending=False)
        if sub_app.empty: continue
        tb = sub_app.iloc[0]
        f1 = f"{tb['macro_f1']:.4f}".replace(".", ",")
        kedua = sub_app.iloc[1] if len(sub_app) > 1 else None
        f1k = f"{kedua['macro_f1']:.4f}".replace(".", ",") if kedua is not None else ""
        warna = warna_aplikasi(app)
        with cols[i]:
            st.markdown(
                f"""
                <div style="padding:1rem; background:#E8F7E8; border-radius:8px; border-left:4px solid {POS};">
                    <div style="color:{warna}; font-size:0.9rem; font-weight:700; margin-bottom:0.2rem;">{app}</div>
                    <div style="color:{HD_DARK}; font-weight:700; font-size:1rem;">Rekomendasi: {tb['model']}</div>
                    <div style="color:#333; font-size:0.82rem; margin-top:0.3rem;">F1-Score: {f1}{f' vs {f1k}' if kedua is not None else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    tutup_kartu()

    col_tabel, col_grafik = st.columns([1.3, 1])
    with col_tabel:
        mulai_kartu(f"Tabel Perbandingan Metrik Evaluasi — {aplikasi}")
        kolom = [
            ("accuracy", "Accuracy"), ("precision_pos", "Precision"),
            ("recall_pos", "Recall"), ("f1_pos", "F1-Score"),
            ("macro_f1", "Macro-F1"),
        ]
        tabel = pd.DataFrame({"Metrik": [n for _, n in kolom]})
        for _, baris in sub.iterrows():
            tabel[baris["model"]] = [
                f"{baris[k]:.4f}".replace(".", ",") if pd.notna(baris[k]) else "-"
                for k, _ in kolom
            ]
        st.table(tabel)
        tutup_kartu()

    with col_grafik:
        mulai_kartu("Grafik F1-Score per Aplikasi")
        fig = px.bar(
            perf, x="aplikasi", y="f1_pos", color="model",
            color_discrete_map={"Naive Bayes": "#A6C9E8", "SVM": HD_DARK,
                                "Complement Naive Bayes": "#A6C9E8"},
            barmode="group",
            text=perf["f1_pos"].apply(lambda v: f"{v:.3f}".replace(".", ",")),
        )
        fig.update_traces(textposition="outside", textfont=dict(size=10))
        fig.update_layout(
            xaxis=dict(title="", tickfont=dict(size=12)),
            yaxis=dict(range=[0, 1.1], title="F1-Score", tickfont=dict(size=11)),
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        tutup_kartu()

    mulai_kartu(f"Confusion Matrix — {terbaik['model']} ({aplikasi})")
    cm_df = pd.DataFrame(
        [["Aktual Positif", int(terbaik["tp"]), int(terbaik["fn"])],
         ["Aktual Negatif", int(terbaik["fp"]), int(terbaik["tn"])]],
        columns=["", "Prediksi Positif", "Prediksi Negatif"],
    )
    st.table(cm_df)
    tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Admin
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    page_title("Halaman Admin")
    data = ringkasan_global()

    mulai_kartu("Unggah Data Ulasan Baru")
    st.caption("Kolom wajib: content, score, at. Maksimal 2.000 ulasan per unggahan.")
    aplikasi = st.radio("Aplikasi", data["aplikasi"], horizontal=True, key="admin_app",
                        label_visibility="collapsed")
    berkas = st.file_uploader("Pilih berkas", type=["csv", "xlsx"], label_visibility="collapsed")
    if st.button("Unggah dan Proses", type="primary", use_container_width=True,
                 disabled=berkas is None):
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
        for _, baris in riwayat.iterrows():
            kol = st.columns([1.5, 1.5, 1.2, 3, 1.5, 1])
            kol[0].write(baris["waktu"].strftime("%d %b %Y %H:%M") if pd.notna(baris["waktu"]) else "-")
            kol[1].write(baris["aplikasi"])
            kol[2].write(baris["username"])
            kol[3].write(baris["berkas"] or "-")
            kol[4].write(f"{int(baris['jumlah_baris']):,} ulasan".replace(",", ".")
                         if pd.notna(baris["jumlah_baris"]) else "-")
            if baris["status"] != "Dibatalkan":
                if kol[5].button("Batal", key=f"batal_{baris['id']}"):
                    batalkan_unggahan(int(baris["id"]))
                    ringkasan_global.clear()
                    riwayat_unggahan.clear()
                    st.rerun()
            else:
                kol[5].caption(baris["status"])
    tutup_kartu()


def proses_unggahan(user: dict, aplikasi: str, berkas) -> None:
    try:
        if berkas.name.lower().endswith(".csv"):
            df = pd.read_csv(berkas)
        else:
            df = pd.read_excel(berkas)
    except Exception as exc:
        st.error(f"Berkas tidak dapat dibaca: {exc}")
        return
    kolom = [c.lower() for c in df.columns]
    hilang = {"content", "score", "at"} - set(kolom)
    if hilang:
        st.error(f"Kolom wajib tidak lengkap: {', '.join(sorted(hilang))}.")
        return
    if len(df) > 2000:
        st.error(f"Jumlah baris ({len(df)}) melebihi batas 2.000 ulasan per unggahan.")
        return
    try:
        eksekusi(
            """
            INSERT INTO riwayat_pelatihan (waktu, id_user, aplikasi, berkas, jumlah_baris, status, catatan)
            VALUES (NOW(), %s, %s, %s, %s, 'Pending', %s)
            """,
            (user["id_user"], aplikasi, berkas.name, len(df),
             "Menunggu pemrosesan oleh skrip pipeline peneliti"),
        )
        st.success(f"Berkas {berkas.name} ({len(df)} ulasan) tercatat.")
    except Exception as exc:
        st.error(f"Gagal mencatat unggahan: {exc}")


def batalkan_unggahan(id_unggahan: int) -> None:
    try:
        eksekusi("UPDATE riwayat_pelatihan SET status = 'Dibatalkan' WHERE id = %s", (id_unggahan,))
    except Exception as exc:
        st.error(f"Gagal membatalkan: {exc}")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def halaman_login() -> None:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-title">Dashboard Analisis Sentimen</div>'
        '<div class="login-subtitle">Instagram · TikTok · X</div>',
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
            if ok:
                st.success(pesan)
            else:
                st.error(pesan)
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
        st.markdown('<div class="sidebar-brand">📊 Dashboard Analisis Sentimen</div>',
                    unsafe_allow_html=True)
        aktif = st.session_state.get("halaman_aktif", "Ringkasan")
        if aktif not in opsi:
            aktif = "Ringkasan"
        pilihan = st.radio("Menu", opsi, index=opsi.index(aktif),
                           key="nav_radio", label_visibility="collapsed")
        if pilihan != aktif:
            st.session_state["halaman_aktif"] = pilihan
            st.rerun()
        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color:#6B7A8F; font-size:0.85rem; padding:0 0.4rem;'>Masuk sebagai "
                    f"<b>{user['username']}</b> ({user['role']})</div>",
                    unsafe_allow_html=True)
        if st.button("Keluar", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()

    if pilihan == "Ringkasan":
        halaman_ringkasan()
    elif pilihan == "Perbandingan Sentimen":
        halaman_sentimen()
    elif pilihan == "Performa Algoritma":
        halaman_performa()
    elif pilihan == "Admin":
        halaman_admin(user)


def main() -> None:
    if "user" not in st.session_state:
        halaman_login()
    else:
        aplikasi_utama()


if __name__ == "__main__":
    main()
