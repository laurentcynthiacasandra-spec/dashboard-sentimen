import os

import bcrypt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

# ---------------------------------------------------------------------------
# Konfigurasi halaman dan tema
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Analisis Sentimen Instagram, TikTok, dan X",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HD = "#175A85"
HD2 = "#1B4F8A"
POS = "#3F8A1E"
NEG = "#D94545"
MUTED = "#6B7A8F"
BG = "#F4F0EE"
CARD_BG = "#FFFFFF"

st.markdown(
    f"""
    <style>
    .stApp {{background: linear-gradient(180deg, #F8F5F3 0%, #EFEAE8 100%);}}
    .main .block-container {{max-width: 1180px; padding-top: 1.2rem; padding-bottom: 3rem;}}

    /* Hide default Streamlit chrome */
    header, footer {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}

    /* Banner header */
    .app-banner {{
        background: linear-gradient(135deg, {HD} 0%, {HD2} 100%);
        color: white;
        padding: 1.4rem 1.6rem;
        border-radius: 14px;
        margin-bottom: 1.6rem;
        box-shadow: 0 4px 16px rgba(23,90,133,0.18);
    }}
    .app-banner h1 {{font-size: 1.5rem; margin: 0; font-weight: 700;}}
    .app-banner .subtitle {{font-size: 0.95rem; opacity: 0.9; margin-top: 0.2rem;}}

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px; background: transparent; border-bottom: none;
        padding: 0 0 4px 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: {CARD_BG}; border-radius: 10px;
        padding: 0.6rem 1.2rem; font-weight: 500;
        border: 1px solid #DDD7D3; color: {HD};
    }}
    .stTabs [aria-selected="true"] {{
        background: {HD}; color: white; border-color: {HD};
        box-shadow: 0 2px 8px rgba(23,90,133,0.3);
    }}

    /* Metric cards */
    .metric-card {{
        background: {CARD_BG}; padding: 1.2rem 1.3rem; border-radius: 12px;
        border: 1px solid #E5DED9;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        height: 100%;
    }}
    .metric-label {{
        color: {MUTED}; font-size: 0.78rem; text-transform: uppercase;
        letter-spacing: 0.5px; font-weight: 600; margin-bottom: 0.4rem;
    }}
    .metric-value {{font-size: 2rem; font-weight: 700; line-height: 1.1; color: {HD};}}
    .metric-sub {{color: {MUTED}; font-size: 0.85rem; margin-top: 0.3rem;}}

    /* Section cards */
    .section-card {{
        background: {CARD_BG}; padding: 1.4rem; border-radius: 12px;
        border: 1px solid #E5DED9;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 1.2rem;
    }}
    .section-title {{
        color: {HD}; font-size: 1.1rem; font-weight: 700;
        margin-bottom: 0.8rem; padding-bottom: 0.4rem;
        border-bottom: 2px solid {HD};
    }}

    /* Insight bullets */
    .insight-row {{
        display: flex; align-items: flex-start; gap: 0.6rem;
        padding: 0.4rem 0; color: #333;
    }}
    .insight-dot {{
        width: 8px; height: 8px; border-radius: 50%;
        background: {HD}; margin-top: 0.5rem; flex-shrink: 0;
    }}

    /* Login card */
    .login-card {{
        background: {CARD_BG}; padding: 2rem 2.2rem; border-radius: 16px;
        border: 1px solid #E5DED9;
        box-shadow: 0 6px 24px rgba(0,0,0,0.08);
        max-width: 420px; margin: 3rem auto;
    }}
    .login-title {{color: {HD}; text-align: center; font-size: 1.8rem; font-weight: 700;}}
    .login-subtitle {{color: {MUTED}; text-align: center; font-size: 0.95rem; margin-bottom: 1.4rem;}}

    /* Buttons */
    .stButton > button {{border-radius: 8px; font-weight: 600;}}
    .stButton > button[kind="primary"] {{
        background: {HD}; border-color: {HD};
    }}
    .stButton > button[kind="primary"]:hover {{
        background: {HD2}; border-color: {HD2};
    }}

    /* Streamlit tables */
    .stTable {{border-radius: 8px; overflow: hidden;}}
    .stTable thead tr th {{background: {HD}; color: white;}}

    /* Sidebar */
    [data-testid="stSidebar"] {{background: {CARD_BG};}}

    /* Date input */
    .stDateInput > div > div {{background: white; border-radius: 8px;}}
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


@st.cache_resource
def get_conn():
    return psycopg2.connect(_get_dsn(), sslmode="require")


def kueri(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            data = cur.fetchall()
        return pd.DataFrame(data, columns=cols)
    except Exception:
        conn.rollback()
        raise


def eksekusi(sql: str, params: tuple = ()) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ---------------------------------------------------------------------------
# Autentikasi
# ---------------------------------------------------------------------------
def masuk(username: str, password: str):
    df = kueri(
        "SELECT id_user, username, password_hash, role FROM users WHERE username = %s",
        (username.strip(),),
    )
    if df.empty:
        return None
    row = df.iloc[0]
    try:
        cocok = bcrypt.checkpw(
            password.encode("utf-8"), row["password_hash"].encode("utf-8")
        )
    except Exception:
        cocok = False
    if not cocok:
        return None
    return {"id_user": int(row["id_user"]), "username": row["username"], "role": row["role"]}


def daftar(username: str, password: str, konfirmasi: str) -> tuple[bool, str]:
    username = username.strip()
    if len(username) < 3:
        return False, "Username minimal 3 karakter."
    if len(password) < 6:
        return False, "Password minimal 6 karakter."
    if password != konfirmasi:
        return False, "Konfirmasi password tidak cocok."
    ada = kueri("SELECT 1 FROM users WHERE username = %s", (username,))
    if not ada.empty:
        return False, "Username sudah terpakai."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    eksekusi(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'Pengguna')",
        (username, hashed),
    )
    return True, "Akun berhasil dibuat. Silakan masuk."


# ---------------------------------------------------------------------------
# Kueri data analitis
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def model_utama_id() -> int:
    """Ambil id_model utama. Pembanding diabaikan supaya tidak dobel hitung."""
    df = kueri(
        "SELECT id_model FROM dim_model WHERE COALESCE(pembanding, FALSE) = FALSE ORDER BY id_model LIMIT 1"
    )
    if not df.empty:
        return int(df.iloc[0]["id_model"])
    df2 = kueri("SELECT MIN(id_model) AS id_min FROM fact_sentimen")
    return int(df2.iloc[0]["id_min"]) if not df2.empty else 1


@st.cache_data(ttl=300, show_spinner=False)
def daftar_aplikasi() -> list:
    df = kueri("SELECT nama_aplikasi FROM dim_aplikasi ORDER BY nama_aplikasi")
    return df["nama_aplikasi"].tolist()


@st.cache_data(ttl=300, show_spinner=False)
def ringkasan_global() -> dict:
    """Total ulasan, rata-rata positif, dan jumlah aplikasi (tanpa dobel)."""
    idm = model_utama_id()
    df = kueri(
        """
        SELECT a.nama_aplikasi AS aplikasi,
               s.label_sentimen AS label,
               COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        WHERE f.id_model = %s
        GROUP BY a.nama_aplikasi, s.label_sentimen
        ORDER BY a.nama_aplikasi, s.label_sentimen
        """,
        (idm,),
    )
    df["label"] = df["label"].str.strip().str.title()
    total_rincian = (
        df.groupby("aplikasi")["jumlah"].sum().reset_index().rename(columns={"jumlah": "total_app"})
    )
    df = df.merge(total_rincian, on="aplikasi")
    total = int(total_rincian["total_app"].sum())
    positif = int(df[df["label"] == "Positif"]["jumlah"].sum())
    pos_pct = (positif / total * 100) if total else 0.0
    aplikasi = sorted(df["aplikasi"].unique())
    return {
        "total": total, "positif_pct": pos_pct,
        "jumlah_aplikasi": len(aplikasi), "aplikasi": aplikasi,
        "rincian": df,
    }


@st.cache_data(ttl=300, show_spinner=False)
def metrik_model() -> pd.DataFrame:
    df = kueri(
        """
        SELECT a.nama_aplikasi AS aplikasi,
               m.nama_model AS model,
               s_akt.label_sentimen AS aktual,
               s_pre.label_sentimen AS prediksi,
               COUNT(*) AS n
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_model m ON m.id_model = f.id_model
        JOIN dim_sentimen s_akt ON s_akt.id_sentimen = f.id_sentimen
        JOIN dim_sentimen s_pre ON s_pre.id_sentimen = f.id_sentimen_prediksi
        WHERE f.data_uji = TRUE
        GROUP BY a.nama_aplikasi, m.nama_model, s_akt.label_sentimen, s_pre.label_sentimen
        ORDER BY a.nama_aplikasi, m.nama_model
        """
    )
    if df.empty:
        return df
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
        prec = tp_ / (tp_ + fp_) if (tp_ + fp_) else 0.0
        rec = tp_ / (tp_ + fn_) if (tp_ + fn_) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return prec, rec, f1

    p_pos, r_pos, f1_pos = _prf(tp, fp, fn)
    p_neg, r_neg, f1_neg = _prf(tn, fn, fp)
    macro_f1 = (f1_pos + f1_neg) / 2
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": acc,
        "precision_pos": p_pos, "recall_pos": r_pos, "f1_pos": f1_pos,
        "precision_neg": p_neg, "recall_neg": r_neg, "f1_neg": f1_neg,
        "macro_f1": macro_f1,
    }


@st.cache_data(ttl=300, show_spinner=False)
def performa_semua() -> pd.DataFrame:
    df = metrik_model()
    if df.empty:
        return df
    baris = []
    for (app, model), grup in df.groupby(["aplikasi", "model"]):
        cm = {(a, p): int(n) for a, p, n in zip(grup["aktual"], grup["prediksi"], grup["n"])}
        hasil = hitung_metrik(cm)
        baris.append({"aplikasi": app, "model": model, **hasil})
    return pd.DataFrame(baris)


@st.cache_data(ttl=300, show_spinner=False)
def rentang_tanggal(aplikasi: str) -> tuple:
    idm = model_utama_id()
    if aplikasi == "Semua":
        df = kueri(
            """
            SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx
            FROM fact_sentimen f
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE f.id_model = %s
            """,
            (idm,),
        )
    else:
        df = kueri(
            """
            SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx
            FROM fact_sentimen f
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            WHERE f.id_model = %s AND a.nama_aplikasi = %s
            """,
            (idm, aplikasi),
        )
    return df.iloc[0]["mn"], df.iloc[0]["mx"]


@st.cache_data(ttl=300, show_spinner=False)
def sentimen_tersaring(aplikasi: str, dari, sampai) -> pd.DataFrame:
    idm = model_utama_id()
    kondisi_app = "" if aplikasi == "Semua" else "AND a.nama_aplikasi = %s"
    param_app = () if aplikasi == "Semua" else (aplikasi,)
    if dari and sampai:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi,
                   s.label_sentimen AS label,
                   COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE f.id_model = %s AND w.tanggal BETWEEN %s AND %s {kondisi_app}
            GROUP BY a.nama_aplikasi, s.label_sentimen
            ORDER BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, (idm, dari, sampai) + param_app)
    else:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi,
                   s.label_sentimen AS label,
                   COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            WHERE f.id_model = %s {kondisi_app}
            GROUP BY a.nama_aplikasi, s.label_sentimen
            ORDER BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, (idm,) + param_app)
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
            FROM riwayat_pelatihan r
            JOIN users u ON u.id_user = r.id_user
            ORDER BY r.waktu DESC
            LIMIT 50
            """
        )
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Komponen visual
# ---------------------------------------------------------------------------
def kartu_metrik(label: str, nilai: str, sub: str = "", warna: str = HD) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{warna};">{nilai}</div>
            {f'<div class="metric-sub">{sub}</div>' if sub else '<div class="metric-sub">&nbsp;</div>'}
        </div>
        """,
        unsafe_allow_html=True,
    )


def banner(judul: str, subjudul: str = "") -> None:
    st.markdown(
        f"""
        <div class="app-banner">
            <h1>{judul}</h1>
            {f'<div class="subtitle">{subjudul}</div>' if subjudul else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def grafik_distribusi(data: dict) -> None:
    rincian = data["rincian"]
    pos_total = int(rincian[rincian["label"] == "Positif"]["jumlah"].sum())
    neg_total = int(rincian[rincian["label"] == "Negatif"]["jumlah"].sum())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Positif", "Negatif"],
                values=[pos_total, neg_total],
                hole=0.6,
                marker=dict(colors=[POS, NEG], line=dict(color="white", width=3)),
                textinfo="label+percent",
                textfont=dict(size=14, color="white", family="Inter, Arial"),
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10), height=320, showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Halaman: Ringkasan
# ---------------------------------------------------------------------------
def halaman_ringkasan() -> None:
    banner("Ringkasan Insight Utama", "Ulasan Instagram, TikTok, dan X dari Google Play Store")
    data = ringkasan_global()

    k1, k2, k3 = st.columns(3)
    with k1:
        kartu_metrik(
            "Total Ulasan",
            f"{data['total']:,}".replace(",", "."),
            f"{data['jumlah_aplikasi']} aplikasi",
        )
    with k2:
        kartu_metrik(
            "Sentimen Positif (Rata-rata)",
            f"{data['positif_pct']:.1f}%".replace(".", ","),
            warna=POS,
        )
    with k3:
        kartu_metrik("Model Terbaik", "SVM", "kernel linear")

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Distribusi Sentimen</div>', unsafe_allow_html=True)
        grafik_distribusi(data)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Insight Utama</div>', unsafe_allow_html=True)

        rincian = data["rincian"]
        pos_app = rincian[rincian["label"] == "Positif"].copy()
        if not pos_app.empty:
            pos_app["pct"] = pos_app["jumlah"] / pos_app["total_app"] * 100
            terbaik = pos_app.sort_values("pct", ascending=False).iloc[0]
            pct_str = f"{terbaik['pct']:.1f}%".replace(".", ",")
            st.markdown(
                f'<div class="insight-row"><div class="insight-dot"></div>'
                f'<div><b>{terbaik["aplikasi"]}</b> memiliki sentimen positif tertinggi ({pct_str}).</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="insight-row"><div class="insight-dot"></div>'
            f'<div>Model <b>SVM</b> memberikan macro-F1 lebih tinggi dibanding Naive Bayes pada ketiga aplikasi.</div></div>',
            unsafe_allow_html=True,
        )
        try:
            tgl = kueri(
                "SELECT MAX(w.tanggal) AS mx FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu"
            ).iloc[0]["mx"]
            if pd.notna(tgl):
                st.markdown(
                    f'<div class="insight-row"><div class="insight-dot"></div>'
                    f'<div>Data terbaru: <b>{tgl.strftime("%d %B %Y")}</b>.</div></div>',
                    unsafe_allow_html=True,
                )
        except Exception:
            pass
        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Perbandingan Sentimen
# ---------------------------------------------------------------------------
def halaman_sentimen() -> None:
    banner("Perbandingan Sentimen", "Pilih aplikasi dan selang waktu untuk menyaring data")
    data = ringkasan_global()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([2, 1.2, 1.2, 0.6])
    with col1:
        aplikasi = st.selectbox(
            "Aplikasi", ["Semua"] + data["aplikasi"], index=0, key="filter_sentimen_app"
        )
    mn, mx = rentang_tanggal(aplikasi)
    with col2:
        dari = st.date_input(
            "Dari", value=None, min_value=mn, max_value=mx,
            key="filter_sentimen_dari", format="DD/MM/YYYY",
        )
    with col3:
        sampai = st.date_input(
            "Sampai", value=None, min_value=mn, max_value=mx,
            key="filter_sentimen_sampai", format="DD/MM/YYYY",
        )
    with col4:
        st.write("")
        st.write("")
        if st.button("Reset", use_container_width=True):
            for k in ["filter_sentimen_dari", "filter_sentimen_sampai"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    if mn and mx:
        st.caption(
            f"Data tersedia pada rentang **{mn.strftime('%d %b %Y')} – {mx.strftime('%d %b %Y')}**."
        )
    st.markdown('</div>', unsafe_allow_html=True)

    if dari and sampai and dari > sampai:
        st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'.")
        return

    df = sentimen_tersaring(aplikasi, dari, sampai)
    if df.empty:
        st.warning("Tidak ada ulasan pada selang waktu ini.")
        return

    pivot = df.pivot(index="aplikasi", columns="label", values="jumlah").fillna(0)
    for kolom in ["Positif", "Negatif"]:
        if kolom not in pivot.columns:
            pivot[kolom] = 0
    pivot["Total"] = pivot["Positif"] + pivot["Negatif"]
    pivot["Positif %"] = (pivot["Positif"] / pivot["Total"] * 100).round(1)
    pivot["Negatif %"] = (pivot["Negatif"] / pivot["Total"] * 100).round(1)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Persentase Sentimen per Aplikasi</div>', unsafe_allow_html=True)
    melt = pivot.reset_index().melt(
        id_vars="aplikasi", value_vars=["Positif %", "Negatif %"],
        var_name="Sentimen", value_name="Persentase",
    )
    melt["Sentimen"] = melt["Sentimen"].str.replace(" %", "")
    fig = px.bar(
        melt, x="Persentase", y="aplikasi", color="Sentimen", orientation="h",
        color_discrete_map={"Positif": POS, "Negatif": NEG}, text="Persentase",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="inside", textfont=dict(color="white", size=13))
    fig.update_layout(
        xaxis=dict(range=[0, 100], title="", showgrid=False, showticklabels=False),
        yaxis=dict(title="", tickfont=dict(size=13)),
        barmode="stack", height=max(220, 70 * len(pivot) + 80),
        margin=dict(l=10, r=10, t=10, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, title=""),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Tabel Perbandingan</div>', unsafe_allow_html=True)
    tampil = pivot.reset_index()[["aplikasi", "Positif", "Negatif", "Total"]].copy()
    tampil.columns = ["Aplikasi", "Positif", "Negatif", "Total"]
    for c in ["Positif", "Negatif", "Total"]:
        tampil[c] = tampil[c].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    st.table(tampil)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Performa
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    banner("Perbandingan Performa Algoritma", "Naive Bayes vs Support Vector Machine")
    data = ringkasan_global()
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    aplikasi = st.selectbox("Aplikasi", data["aplikasi"], key="filter_performa_app")
    st.markdown('</div>', unsafe_allow_html=True)

    perf = performa_semua()
    if perf.empty:
        st.info("Metrik performa belum tersedia pada fact_sentimen (data_uji).")
        return
    sub = perf[perf["aplikasi"] == aplikasi].sort_values("model")
    if sub.empty:
        st.warning(f"Tidak ada data performa untuk aplikasi {aplikasi}.")
        return

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Macro-F1 (data uji)</div>', unsafe_allow_html=True)
    fig = px.bar(
        sub, x="macro_f1", y="model", orientation="h", color="model",
        color_discrete_map={
            "Naive Bayes": "#2A79D6", "SVM": HD2,
            "Complement Naive Bayes": "#2A79D6",
        },
        text="macro_f1",
    )
    fig.update_traces(texttemplate="%{text:.4f}", textposition="outside", textfont=dict(size=13))
    fig.update_layout(
        xaxis=dict(range=[0, 1.05], title="", showgrid=False, showticklabels=False),
        yaxis=dict(title="", tickfont=dict(size=13)),
        showlegend=False, height=200, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]["model"]
    st.success(f"Model terbaik untuk **{aplikasi}**: **{terbaik}**")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Metrik Evaluasi</div>', unsafe_allow_html=True)
    kolom = [
        ("accuracy", "Accuracy"),
        ("precision_pos", "Precision (+)"),
        ("recall_pos", "Recall (+)"),
        ("f1_pos", "F1 (+)"),
        ("precision_neg", "Precision (−)"),
        ("recall_neg", "Recall (−)"),
        ("f1_neg", "F1 (−)"),
        ("macro_f1", "Macro-F1"),
    ]
    tabel = pd.DataFrame({"Metrik": [n for _, n in kolom]})
    for _, baris in sub.iterrows():
        tabel[baris["model"]] = [
            f"{baris[k]:.4f}".replace(".", ",") if pd.notna(baris[k]) else "-"
            for k, _ in kolom
        ]
    st.table(tabel)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">Confusion Matrix ({terbaik})</div>', unsafe_allow_html=True)
    bar_terbaik = sub[sub["model"] == terbaik].iloc[0]
    cm_df = pd.DataFrame(
        [
            ["Aktual Positif", int(bar_terbaik["tp"]), int(bar_terbaik["fn"])],
            ["Aktual Negatif", int(bar_terbaik["fp"]), int(bar_terbaik["tn"])],
        ],
        columns=["", "Prediksi Positif", "Prediksi Negatif"],
    )
    st.table(cm_df)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Admin
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    banner("Halaman Admin", "Unggah data ulasan baru dan kelola riwayat unggahan")
    data = ringkasan_global()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Unggah Data Ulasan Baru</div>', unsafe_allow_html=True)
    aplikasi = st.selectbox("Aplikasi", data["aplikasi"], key="admin_app")
    berkas = st.file_uploader(
        "Berkas ulasan (.csv atau .xlsx dengan kolom: content, score, at)",
        type=["csv", "xlsx"],
    )
    if st.button("Unggah dan Proses", type="primary", use_container_width=True):
        if berkas is None:
            st.error("Pilih berkas terlebih dahulu.")
        else:
            proses_unggahan(user, aplikasi, berkas)
            ringkasan_global.clear()
            riwayat_unggahan.clear()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Riwayat Unggahan</div>', unsafe_allow_html=True)
    riwayat = riwayat_unggahan()
    if riwayat.empty:
        st.info("Belum ada unggahan.")
    else:
        for _, baris in riwayat.iterrows():
            kolom = st.columns([2, 2, 2, 3, 2, 1])
            kolom[0].write(
                baris["waktu"].strftime("%d %b %Y %H:%M") if pd.notna(baris["waktu"]) else "-"
            )
            kolom[1].write(baris["aplikasi"])
            kolom[2].write(baris["username"])
            kolom[3].write(baris["berkas"] or "-")
            kolom[4].write(
                f"{int(baris['jumlah_baris']):,} ulasan".replace(",", ".")
                if pd.notna(baris["jumlah_baris"]) else "-"
            )
            if baris["status"] not in ("Dibatalkan",):
                if kolom[5].button("Batal", key=f"batal_{baris['id']}"):
                    batalkan_unggahan(int(baris["id"]))
                    ringkasan_global.clear()
                    riwayat_unggahan.clear()
                    st.rerun()
            else:
                kolom[5].caption(baris["status"])
    st.markdown('</div>', unsafe_allow_html=True)


def proses_unggahan(user: dict, aplikasi: str, berkas) -> None:
    try:
        if berkas.name.lower().endswith(".csv"):
            df = pd.read_csv(berkas)
        else:
            df = pd.read_excel(berkas)
    except Exception as exc:
        st.error(f"Berkas tidak dapat dibaca: {exc}")
        return
    kolom_rendah = [c.lower() for c in df.columns]
    wajib = {"content", "score", "at"}
    hilang = wajib - set(kolom_rendah)
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
            (
                user["id_user"], aplikasi, berkas.name, len(df),
                "Menunggu pemrosesan oleh skrip pipeline peneliti",
            ),
        )
        st.success(
            f"Berkas {berkas.name} ({len(df)} ulasan) tercatat pada riwayat sebagai 'Pending'. "
            "Pemrosesan pelabelan dan prediksi dijalankan oleh skrip pipeline peneliti."
        )
    except Exception as exc:
        st.error(f"Gagal mencatat unggahan: {exc}")


def batalkan_unggahan(id_unggahan: int) -> None:
    try:
        eksekusi(
            "UPDATE riwayat_pelatihan SET status = 'Dibatalkan' WHERE id = %s",
            (id_unggahan,),
        )
        st.success("Unggahan dibatalkan.")
    except Exception as exc:
        st.error(f"Gagal membatalkan: {exc}")


# ---------------------------------------------------------------------------
# Halaman: Login dan Daftar
# ---------------------------------------------------------------------------
def halaman_login() -> None:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="login-title">Analisis Sentimen</div>'
        f'<div class="login-subtitle">Instagram · TikTok · X</div>',
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
# Routing utama
# ---------------------------------------------------------------------------
def aplikasi_utama() -> None:
    user = st.session_state["user"]
    with st.sidebar:
        st.markdown(f"**{user['username']}**  \nPeran: `{user['role']}`")
        if st.button("Keluar", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
        st.divider()
        st.caption("Analisis Sentimen Instagram, TikTok, dan X")
        st.caption("Universitas Tarumanagara")

    if user["role"] == "Admin":
        tab_ring, tab_sent, tab_perf, tab_adm = st.tabs(
            ["Ringkasan", "Sentimen", "Performa", "Admin"]
        )
        with tab_ring:
            halaman_ringkasan()
        with tab_sent:
            halaman_sentimen()
        with tab_perf:
            halaman_performa()
        with tab_adm:
            halaman_admin(user)
    else:
        tab_ring, tab_sent, tab_perf = st.tabs(["Ringkasan", "Sentimen", "Performa"])
        with tab_ring:
            halaman_ringkasan()
        with tab_sent:
            halaman_sentimen()
        with tab_perf:
            halaman_performa()


def main() -> None:
    if "user" not in st.session_state:
        halaman_login()
    else:
        aplikasi_utama()


if __name__ == "__main__":
    main()
