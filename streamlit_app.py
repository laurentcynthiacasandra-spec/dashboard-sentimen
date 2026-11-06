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
    page_title="Dashboard Analisis Sentimen",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HD = "#175A85"
HD_DARK = "#0F3F5E"
POS = "#3F8A1E"
NEG = "#D94545"
NEG_SOFT = "#F3C8C8"
POS_SOFT = "#CFE4C1"
MUTED = "#6B7A8F"
BG = "#F4F0EE"
CARD_BG = "#FFFFFF"
BORDER = "#E5DED9"

st.markdown(
    f"""
    <style>
    .stApp {{background: #F8F5F3;}}
    .main .block-container {{max-width: 1200px; padding-top: 0; padding-bottom: 3rem;}}
    header, footer {{visibility: hidden;}}
    #MainMenu {{visibility: hidden;}}

    /* Blue navigation header bar (seperti mockup) */
    .nav-header {{
        background: {HD};
        color: white;
        padding: 0.9rem 1.4rem;
        margin: -1rem -1rem 1.4rem -1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-radius: 0 0 4px 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .nav-title {{font-weight: 700; font-size: 1.05rem;}}
    .nav-user {{font-size: 0.85rem; opacity: 0.9;}}

    /* Tab bar — mirip nav pills horizontal pada mockup */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 6px;
        margin-bottom: 1.4rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; border-radius: 8px;
        padding: 0.55rem 1.2rem; font-weight: 500;
        border: none; color: {MUTED};
        margin: 0;
    }}
    .stTabs [aria-selected="true"] {{
        background: {HD}; color: white;
    }}

    /* Kartu metrik 4 kolom */
    .metric-card {{
        background: {CARD_BG};
        padding: 1rem 1.1rem;
        border-radius: 10px;
        border: 1px solid {BORDER};
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        min-height: 110px;
    }}
    .metric-label {{
        color: {MUTED}; font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.5px; font-weight: 600; margin-bottom: 0.3rem;
    }}
    .metric-value {{
        font-size: 1.7rem; font-weight: 700; line-height: 1.1;
    }}
    .metric-sub {{color: {MUTED}; font-size: 0.78rem; margin-top: 0.3rem;}}

    /* Kartu berisi grafik dan tabel */
    .section-card {{
        background: {CARD_BG}; padding: 1.1rem 1.2rem; border-radius: 10px;
        border: 1px solid {BORDER};
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        margin-bottom: 1.1rem;
    }}
    .section-title {{
        color: {HD}; font-size: 1rem; font-weight: 700;
        margin-bottom: 0.7rem; padding-bottom: 0.4rem;
    }}

    /* Bullet insight */
    .insight-row {{
        display: flex; align-items: flex-start; gap: 0.6rem;
        padding: 0.35rem 0; color: #333; font-size: 0.93rem;
    }}
    .insight-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: {HD}; margin-top: 0.5rem; flex-shrink: 0;
    }}

    /* Login card */
    .login-wrap {{
        max-width: 420px; margin: 3rem auto;
        background: {CARD_BG}; padding: 2rem 2.2rem; border-radius: 14px;
        border: 1px solid {BORDER}; box-shadow: 0 6px 24px rgba(0,0,0,0.08);
    }}
    .login-title {{color: {HD}; text-align: center; font-size: 1.7rem; font-weight: 700; margin: 0;}}
    .login-subtitle {{color: {MUTED}; text-align: center; font-size: 0.9rem; margin-bottom: 1.4rem;}}

    /* Buttons */
    .stButton > button {{border-radius: 8px; font-weight: 600;}}
    .stButton > button[kind="primary"] {{background: {HD}; border-color: {HD};}}
    .stButton > button[kind="primary"]:hover {{background: {HD_DARK}; border-color: {HD_DARK};}}

    /* Table styling */
    .stTable thead tr th {{background: {HD}; color: white; font-size: 0.85rem;}}
    .stTable tbody tr td {{font-size: 0.88rem;}}

    [data-testid="stSidebar"] {{background: {CARD_BG};}}

    /* Radio (filter aplikasi mirip pill) */
    .stRadio [role="radiogroup"] {{
        display: flex; gap: 6px; flex-wrap: wrap;
    }}
    .stRadio [role="radiogroup"] label {{
        background: {CARD_BG}; border: 1px solid {BORDER};
        padding: 0.4rem 0.9rem; border-radius: 20px;
        cursor: pointer; margin: 0;
    }}
    .stRadio [role="radiogroup"] label:has(input:checked) {{
        background: {HD}; color: white; border-color: {HD};
    }}
    .stRadio [role="radiogroup"] label > div:first-child {{display: none;}}
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
        cocok = bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8"))
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
    df = kueri(
        "SELECT id_model FROM dim_model WHERE COALESCE(pembanding, FALSE) = FALSE ORDER BY id_model LIMIT 1"
    )
    if not df.empty:
        return int(df.iloc[0]["id_model"])
    df2 = kueri("SELECT MIN(id_model) AS id_min FROM fact_sentimen")
    return int(df2.iloc[0]["id_min"]) if not df2.empty else 1


@st.cache_data(ttl=300, show_spinner=False)
def ringkasan_global() -> dict:
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
            "SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx "
            "FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu "
            "WHERE f.id_model = %s",
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
    kondisi_app = "" if aplikasi == "Semua" else "AND a.nama_aplikasi = %s"
    param_app = () if aplikasi == "Semua" else (aplikasi,)
    if dari and sampai:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi, s.label_sentimen AS label, COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE f.id_model = %s AND w.tanggal BETWEEN %s AND %s {kondisi_app}
            GROUP BY a.nama_aplikasi, s.label_sentimen
        """
        df = kueri(sql, (idm, dari, sampai) + param_app)
    else:
        sql = f"""
            SELECT a.nama_aplikasi AS aplikasi, s.label_sentimen AS label, COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            WHERE f.id_model = %s {kondisi_app}
            GROUP BY a.nama_aplikasi, s.label_sentimen
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
            ORDER BY r.waktu DESC LIMIT 50
            """
        )
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Komponen visual
# ---------------------------------------------------------------------------
def nav_header(username: str, role: str) -> None:
    st.markdown(
        f"""
        <div class="nav-header">
            <div class="nav-title">📊 Dashboard Analisis Sentimen</div>
            <div class="nav-user">{username} · {role}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kartu_metrik(label: str, nilai: str, sub: str = "", warna: str = HD) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{warna};">{nilai}</div>
            <div class="metric-sub">{sub or '&nbsp;'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Halaman: Ringkasan
# ---------------------------------------------------------------------------
def halaman_ringkasan() -> None:
    data = ringkasan_global()

    # 4 kartu metrik mirip mockup
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kartu_metrik(
            "Total Ulasan Dianalisis",
            f"{data['total']:,}".replace(",", "."),
            f"{data['jumlah_aplikasi']} aplikasi",
        )
    with k2:
        kartu_metrik(
            "Rata-rata Sentimen Positif",
            f"{data['positif_pct']:.1f}%".replace(".", ","),
            "dari seluruh ulasan",
            warna=POS,
        )
    with k3:
        kartu_metrik(
            "Algoritma Terbaik",
            "SVM",
            "unggul di 3 aplikasi",
            warna=HD,
        )
    with k4:
        tgl_str = (
            data["tanggal_terbaru"].strftime("%d %b %Y")
            if pd.notna(data["tanggal_terbaru"]) else "-"
        )
        kartu_metrik("Data Terakhir Diperbarui", tgl_str, "data Admin otomatis")

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Dua kolom: bar chart kiri, donut kanan
    col_bar, col_pie = st.columns([1.2, 1])
    rincian = data["rincian"]

    with col_bar:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Perbandingan Sentimen Positif per Aplikasi</div>', unsafe_allow_html=True)
        pos_app = rincian[rincian["label"] == "Positif"].copy()
        pos_app["pct"] = (pos_app["jumlah"] / pos_app["total_app"] * 100).round(1)
        pos_app = pos_app.sort_values("pct", ascending=True)
        fig = px.bar(
            pos_app, x="pct", y="aplikasi", orientation="h",
            text="pct", color_discrete_sequence=[HD],
        )
        fig.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside",
            textfont=dict(size=13, color=HD),
            marker=dict(line=dict(width=0)),
        )
        fig.update_layout(
            xaxis=dict(range=[0, 100], title="", showgrid=False, showticklabels=False),
            yaxis=dict(title="", tickfont=dict(size=13)),
            height=240, margin=dict(l=10, r=40, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_pie:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Distribusi Sentimen Keseluruhan</div>', unsafe_allow_html=True)
        pos_total = int(rincian[rincian["label"] == "Positif"]["jumlah"].sum())
        neg_total = int(rincian[rincian["label"] == "Negatif"]["jumlah"].sum())
        fig = go.Figure(data=[go.Pie(
            labels=[f"Positif ({data['positif_pct']:.1f}%)".replace(".", ","),
                    f"Negatif ({100 - data['positif_pct']:.1f}%)".replace(".", ",")],
            values=[pos_total, neg_total],
            marker=dict(colors=[POS, NEG], line=dict(color="white", width=2)),
            textinfo="none",
            hovertemplate="%{label}<br>%{value:,} ulasan<extra></extra>",
        )])
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), height=240,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Insight Utama
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Insight Utama</div>', unsafe_allow_html=True)
    pos_app_sorted = pos_app.sort_values("pct", ascending=False)
    if not pos_app_sorted.empty:
        terbaik = pos_app_sorted.iloc[0]
        pct = f"{terbaik['pct']:.1f}%".replace(".", ",")
        st.markdown(
            f'<div class="insight-row"><div class="insight-dot"></div>'
            f'<div><b>{terbaik["aplikasi"]}</b> memiliki proporsi sentimen positif tertinggi ({pct}) di antara ketiga aplikasi.</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="insight-row"><div class="insight-dot"></div>'
        f'<div>Model <b>SVM</b> secara konsisten unggul pada ketiga aplikasi dibandingkan Naive Bayes berdasarkan macro-F1.</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="insight-row"><div class="insight-dot"></div>'
        f'<div>Pelabelan dilakukan secara <b>hybrid</b> dengan leksikon InSet dan skor rating, dengan penyesuaian valensi pada kata bentrok.</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Perbandingan Sentimen
# ---------------------------------------------------------------------------
def halaman_sentimen() -> None:
    data = ringkasan_global()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 1.2, 1.2])
    with col1:
        opsi_app = ["Semua"] + data["aplikasi"]
        aplikasi = st.radio(
            "Filter Aplikasi", opsi_app, horizontal=True,
            key="filter_sentimen_app", label_visibility="collapsed",
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
    for kol in ["Positif", "Negatif"]:
        if kol not in pivot.columns:
            pivot[kol] = 0
    pivot["Total"] = pivot["Positif"] + pivot["Negatif"]
    pivot["Positif %"] = (pivot["Positif"] / pivot["Total"] * 100).round(1)
    pivot["Negatif %"] = (pivot["Negatif"] / pivot["Total"] * 100).round(1)
    pivot = pivot.reset_index()

    # Grouped bar chart mirip mockup (vertical bars berdampingan per aplikasi)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Perbandingan Proporsi Sentimen Positif vs Negatif</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Positif", x=pivot["aplikasi"], y=pivot["Positif %"],
        marker_color=POS, text=pivot["Positif %"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
        textposition="inside", textfont=dict(color="white", size=13, family="Arial"),
    ))
    fig.add_trace(go.Bar(
        name="Negatif", x=pivot["aplikasi"], y=pivot["Negatif %"],
        marker_color=NEG, text=pivot["Negatif %"].apply(lambda v: f"{v:.1f}%".replace(".", ",")),
        textposition="inside", textfont=dict(color="white", size=13, family="Arial"),
    ))
    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="", tickfont=dict(size=13)),
        yaxis=dict(title="Persentase", range=[0, 100], tickfont=dict(size=12)),
        height=360, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=""),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Tabel Perbandingan</div>', unsafe_allow_html=True)
    tampil = pivot[["aplikasi", "Positif", "Negatif", "Total"]].copy()
    tampil.columns = ["Aplikasi", "Positif", "Negatif", "Total"]
    for c in ["Positif", "Negatif", "Total"]:
        tampil[c] = tampil[c].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    st.table(tampil)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Performa Algoritma
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    data = ringkasan_global()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    aplikasi = st.radio(
        "Pilih Aplikasi", data["aplikasi"], horizontal=True, key="filter_performa_app",
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    perf = performa_semua()
    if perf.empty:
        st.info("Metrik performa belum tersedia pada fact_sentimen (data_uji).")
        return
    sub = perf[perf["aplikasi"] == aplikasi].sort_values("model")
    if sub.empty:
        st.warning(f"Tidak ada data performa untuk aplikasi {aplikasi}.")
        return

    # Rekomendasi per aplikasi (semua)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Rekomendasi Algoritma per Aplikasi</div>', unsafe_allow_html=True)
    cols = st.columns(len(data["aplikasi"]))
    for i, app in enumerate(data["aplikasi"]):
        sub_app = perf[perf["aplikasi"] == app].sort_values("macro_f1", ascending=False)
        if sub_app.empty:
            continue
        terbaik = sub_app.iloc[0]
        kedua = sub_app.iloc[1] if len(sub_app) > 1 else None
        with cols[i]:
            st.markdown(
                f"""
                <div style="padding:1rem; background:{POS_SOFT}; border-radius:8px; border-left:4px solid {POS};">
                    <div style="color:{MUTED}; font-size:0.78rem; text-transform:uppercase; font-weight:600;">{app}</div>
                    <div style="color:{HD_DARK}; font-weight:700; font-size:1rem; margin:0.2rem 0;">Rekomendasi: {terbaik['model']}</div>
                    <div style="color:#333; font-size:0.82rem;">
                        Macro-F1: {str(round(terbaik['macro_f1'], 4)).replace('.', ',')}
                        {f" vs {str(round(kedua['macro_f1'], 4)).replace('.', ',')}" if kedua is not None else ""}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)

    # Tabel metrik dan grafik
    kol_tab, kol_graf = st.columns([1.3, 1])

    with kol_tab:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">Tabel Metrik Evaluasi — {aplikasi}</div>', unsafe_allow_html=True)
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

    with kol_graf:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Grafik Macro-F1</div>', unsafe_allow_html=True)
        fig = px.bar(
            sub, x="model", y="macro_f1", color="model",
            color_discrete_map={
                "Naive Bayes": "#2A79D6", "SVM": HD_DARK,
                "Complement Naive Bayes": "#2A79D6",
            },
            text="macro_f1",
        )
        fig.update_traces(
            texttemplate="%{text:.4f}", textposition="outside", textfont=dict(size=13),
        )
        fig.update_layout(
            xaxis=dict(title="", tickfont=dict(size=12)),
            yaxis=dict(range=[0, 1.05], title="", showgrid=True, gridcolor="#eee"),
            showlegend=False, height=280, margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Confusion matrix terbaik
    terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-title">Confusion Matrix — {terbaik["model"]} ({aplikasi})</div>',
        unsafe_allow_html=True,
    )
    cm_df = pd.DataFrame(
        [
            ["Aktual Positif", int(terbaik["tp"]), int(terbaik["fn"])],
            ["Aktual Negatif", int(terbaik["fp"]), int(terbaik["tn"])],
        ],
        columns=["", "Prediksi Positif", "Prediksi Negatif"],
    )
    st.table(cm_df)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Halaman: Admin
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    data = ringkasan_global()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Unggah Data Ulasan Baru</div>', unsafe_allow_html=True)
    aplikasi = st.radio(
        "Pilih Aplikasi Target", data["aplikasi"], horizontal=True, key="admin_app",
    )
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
    st.markdown('<div class="section-title">Riwayat Pelatihan dan Unggahan</div>', unsafe_allow_html=True)
    riwayat = riwayat_unggahan()
    if riwayat.empty:
        st.info("Belum ada unggahan.")
    else:
        for _, baris in riwayat.iterrows():
            kol = st.columns([2, 2, 2, 3, 2, 1])
            kol[0].write(
                baris["waktu"].strftime("%d %b %Y %H:%M") if pd.notna(baris["waktu"]) else "-"
            )
            kol[1].write(baris["aplikasi"])
            kol[2].write(baris["username"])
            kol[3].write(baris["berkas"] or "-")
            kol[4].write(
                f"{int(baris['jumlah_baris']):,} ulasan".replace(",", ".")
                if pd.notna(baris["jumlah_baris"]) else "-"
            )
            if baris["status"] not in ("Dibatalkan",):
                if kol[5].button("Batal", key=f"batal_{baris['id']}"):
                    batalkan_unggahan(int(baris["id"]))
                    ringkasan_global.clear()
                    riwayat_unggahan.clear()
                    st.rerun()
            else:
                kol[5].caption(baris["status"])
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
            f"Berkas {berkas.name} ({len(df)} ulasan) tercatat pada riwayat sebagai 'Pending'."
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
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-title">Dashboard Analisis Sentimen</div>'
        '<div class="login-subtitle">Instagram · TikTok · X · Google Play Store</div>',
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
    nav_header(user["username"], user["role"])
    with st.sidebar:
        st.markdown(f"**{user['username']}**  \nPeran: `{user['role']}`")
        if st.button("Keluar", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
        st.divider()
        st.caption("Dashboard Analisis Sentimen")
        st.caption("Universitas Tarumanagara")

    if user["role"] == "Admin":
        tab_ring, tab_sent, tab_perf, tab_adm = st.tabs(
            ["Ringkasan", "Perbandingan Sentimen", "Performa Algoritma", "Admin"]
        )
        with tab_ring: halaman_ringkasan()
        with tab_sent: halaman_sentimen()
        with tab_perf: halaman_performa()
        with tab_adm:  halaman_admin(user)
    else:
        tab_ring, tab_sent, tab_perf = st.tabs(
            ["Ringkasan", "Perbandingan Sentimen", "Performa Algoritma"]
        )
        with tab_ring: halaman_ringkasan()
        with tab_sent: halaman_sentimen()
        with tab_perf: halaman_performa()


def main() -> None:
    if "user" not in st.session_state:
        halaman_login()
    else:
        aplikasi_utama()


if __name__ == "__main__":
    main()
