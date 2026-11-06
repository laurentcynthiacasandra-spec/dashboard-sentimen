import os

import bcrypt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analisis Sentimen",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

HD = "#175A85"
HD_DARK = "#0F3F5E"
HD_SOFT = "#E8F1F7"
POS = "#3F8A1E"
NEG = "#D94545"
MUTED = "#6B7A8F"
CARD_BG = "#FFFFFF"
BORDER = "#E5DED9"
PAGE_BG = "#F4F0EE"

st.markdown(
    f"""
    <style>
    /* Reset Streamlit chrome */
    header, footer, #MainMenu {{visibility: hidden;}}
    .stApp {{background: {PAGE_BG};}}

    /* Container, batasi lebar supaya terasa seperti mobile di desktop */
    .main .block-container {{
        max-width: 560px;
        padding: 0 1rem 2rem 1rem;
    }}
    @media (min-width: 992px) {{
        .main .block-container {{max-width: 720px;}}
    }}

    /* Blue header bar per halaman */
    .page-header {{
        background: {HD};
        color: white;
        padding: 1rem 1.2rem;
        margin: -0.5rem -1rem 1.2rem -1rem;
        display: flex; align-items: center; justify-content: space-between;
        border-radius: 0 0 14px 14px;
        box-shadow: 0 2px 10px rgba(23,90,133,0.2);
    }}
    .page-header .page-title {{
        font-size: 1.15rem; font-weight: 700; margin: 0;
    }}
    .page-header .page-user {{
        font-size: 0.8rem; opacity: 0.85;
    }}

    /* Tab bar — pill horizontal */
    .stTabs {{margin-top: 0;}}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0; background: transparent; border-bottom: none;
        padding: 0; margin-bottom: 1.1rem; justify-content: center;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: {CARD_BG}; color: {MUTED};
        padding: 0.5rem 1.1rem; margin: 0 2px;
        border: 1px solid {BORDER}; border-radius: 20px;
        font-weight: 500; font-size: 0.88rem;
    }}
    .stTabs [aria-selected="true"] {{
        background: {HD}; color: white; border-color: {HD};
    }}
    .stTabs [data-baseweb="tab-highlight"] {{display: none;}}

    /* Kartu umum */
    .kartu {{
        background: {CARD_BG};
        padding: 1rem 1.1rem;
        border-radius: 12px;
        border: 1px solid {BORDER};
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        margin-bottom: 0.9rem;
    }}
    .kartu-judul {{
        color: {HD}; font-weight: 700; font-size: 1rem;
        margin-bottom: 0.7rem;
    }}

    /* Kartu metrik (label kecil + angka besar) */
    .kartu-metrik {{
        background: {CARD_BG};
        padding: 0.9rem 1.1rem;
        border-radius: 12px;
        border: 1px solid {BORDER};
        margin-bottom: 0.8rem;
    }}
    .metrik-label {{
        color: {MUTED}; font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.5px; font-weight: 600;
    }}
    .metrik-nilai {{
        font-size: 1.9rem; font-weight: 700; line-height: 1.1;
        margin-top: 0.2rem;
    }}
    .metrik-nilai-sedang {{
        font-size: 1.2rem; font-weight: 700; line-height: 1.2;
        margin-top: 0.2rem;
    }}
    .metrik-sub {{
        color: {MUTED}; font-size: 0.78rem; margin-top: 0.2rem;
    }}

    /* Insight bullet */
    .insight {{display: flex; gap: 0.6rem; padding: 0.3rem 0; align-items: flex-start;}}
    .insight-dot {{
        width: 6px; height: 6px; border-radius: 50%;
        background: #9CC3E4; margin-top: 0.55rem; flex-shrink: 0;
    }}
    .insight-text {{font-size: 0.9rem; color: #333; line-height: 1.45;}}

    /* Bar inline untuk Sentimen (horizontal stacked) */
    .bar-inline {{
        display: flex; width: 100%; height: 32px; border-radius: 4px;
        overflow: hidden; margin: 0.3rem 0;
    }}
    .bar-pos {{background: {POS}; display: flex; align-items: center;
        padding: 0 0.6rem; color: white; font-weight: 700; font-size: 0.82rem;}}
    .bar-neg {{background: {NEG}; display: flex; align-items: center; justify-content: flex-end;
        padding: 0 0.6rem; color: white; font-weight: 700; font-size: 0.82rem;}}
    .bar-label {{font-weight: 600; margin-bottom: 0.1rem; font-size: 0.9rem;}}
    .legend-row {{display: flex; gap: 1rem; font-size: 0.82rem; margin-top: 0.4rem;}}
    .legend-dot {{display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: middle;}}

    /* Login */
    .login-card {{
        background: {CARD_BG}; padding: 1.8rem 1.6rem; border-radius: 14px;
        border: 1px solid {BORDER}; box-shadow: 0 6px 24px rgba(0,0,0,0.06);
        max-width: 400px; margin: 2rem auto;
    }}
    .login-title {{color: {HD}; text-align: center; font-size: 1.5rem; font-weight: 700; margin: 0;}}
    .login-subtitle {{color: {MUTED}; text-align: center; font-size: 0.85rem; margin-bottom: 1.2rem;}}

    /* Tombol */
    .stButton > button {{border-radius: 8px; font-weight: 600;}}
    .stButton > button[kind="primary"] {{background: {HD}; border-color: {HD};}}
    .stButton > button[kind="primary"]:hover {{background: {HD_DARK}; border-color: {HD_DARK};}}

    /* Radio pill (filter aplikasi) */
    div[role="radiogroup"] {{
        display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 0.3rem;
    }}
    div[role="radiogroup"] label {{
        background: {CARD_BG}; border: 1px solid {BORDER};
        padding: 0.35rem 0.9rem; border-radius: 18px;
        margin: 0; cursor: pointer;
    }}
    div[role="radiogroup"] label:has(input:checked) {{
        background: {HD}; color: white; border-color: {HD};
    }}
    div[role="radiogroup"] label > div:first-child {{display: none;}}

    /* Tabel */
    .stTable {{border-radius: 8px; overflow: hidden;}}
    .stTable thead tr th {{background: {HD_SOFT}; color: {HD_DARK}; font-weight: 700; font-size: 0.82rem;}}
    .stTable tbody tr td {{font-size: 0.85rem;}}

    [data-testid="stSidebar"] {{background: {CARD_BG};}}

    /* Status offline notice bar */
    .mode-offline {{
        background: #FFF3C4; color: #6B5300;
        padding: 0.5rem 1rem; text-align: center;
        border-radius: 8px; font-size: 0.85rem;
        margin-bottom: 0.8rem;
    }}
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
# Kueri data
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
    if df.empty:
        return df
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
def page_header(judul: str, username: str = "") -> None:
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-title">{judul}</div>
            <div class="page-user">{username}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kartu_metrik(label: str, nilai: str, sub: str = "", warna: str = HD, besar: bool = True) -> None:
    kelas_nilai = "metrik-nilai" if besar else "metrik-nilai-sedang"
    st.markdown(
        f"""
        <div class="kartu-metrik">
            <div class="metrik-label">{label}</div>
            <div class="{kelas_nilai}" style="color:{warna};">{nilai}</div>
            {f'<div class="metrik-sub">{sub}</div>' if sub else ''}
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
    data = ringkasan_global()
    tgl_str = (
        data["tanggal_terbaru"].strftime("%Y-%m-%d")
        if pd.notna(data["tanggal_terbaru"]) else "-"
    )

    kartu_metrik("Total Ulasan", f"{data['total']:,}".replace(",", "."), f"{data['jumlah_aplikasi']} aplikasi")
    kartu_metrik("Sentimen Positif (Rata-rata)", f"{data['positif_pct']:.1f}%".replace(".", ","), warna=POS)
    kartu_metrik("Model Terbaik", "SVM", f"Data terbaru: {tgl_str}", besar=False)

    # Distribusi Sentimen (donut + legend)
    mulai_kartu("Distribusi Sentimen")
    rincian = data["rincian"]
    pos_total = int(rincian[rincian["label"] == "Positif"]["jumlah"].sum())
    neg_total = int(rincian[rincian["label"] == "Negatif"]["jumlah"].sum())
    pos_pct = data["positif_pct"]
    neg_pct = 100 - pos_pct
    fig = go.Figure(data=[go.Pie(
        labels=[f"Positif {pos_pct:.1f}%".replace(".", ","),
                f"Negatif {neg_pct:.1f}%".replace(".", ",")],
        values=[pos_total, neg_total],
        marker=dict(colors=[POS, NEG], line=dict(color="white", width=2)),
        textinfo="none", hole=0.5,
        hovertemplate="%{label}<br>%{value:,} ulasan<extra></extra>",
    )])
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=240,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.0, font=dict(size=12)),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    tutup_kartu()

    # Insight Utama
    mulai_kartu("Insight Utama")
    pos_app = rincian[rincian["label"] == "Positif"].copy()
    pos_app["pct"] = (pos_app["jumlah"] / pos_app["total_app"] * 100).round(1)
    pos_app_sorted = pos_app.sort_values("pct", ascending=False)
    if len(pos_app_sorted) >= 1:
        tgi = pos_app_sorted.iloc[0]
        trd = pos_app_sorted.iloc[-1] if len(pos_app_sorted) > 1 else None
        if trd is not None:
            t1 = f"{tgi['pct']:.1f}%".replace('.', ',')
            t2 = f"{trd['pct']:.1f}%".replace('.', ',')
            st.markdown(
                f'<div class="insight"><div class="insight-dot"></div>'
                f'<div class="insight-text"><b>{tgi["aplikasi"]}</b> memiliki proporsi sentimen positif tertinggi '
                f'({t1}), sedangkan <b>{trd["aplikasi"]}</b> terendah ({t2}).</div></div>',
                unsafe_allow_html=True,
            )
    st.markdown(
        '<div class="insight"><div class="insight-dot"></div>'
        '<div class="insight-text">Pada ketiga aplikasi, model terbaik adalah <b>SVM (kernel linear)</b>.</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="insight"><div class="insight-dot"></div>'
        '<div class="insight-text">Pelabelan dilakukan secara hybrid (leksikon InSet + skor rating) dengan penyesuaian valensi pada kata bentrok.</div></div>',
        unsafe_allow_html=True,
    )
    tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Perbandingan Sentimen
# ---------------------------------------------------------------------------
def halaman_sentimen() -> None:
    data = ringkasan_global()
    opsi = ["Semua"] + data["aplikasi"]
    aplikasi = st.radio("Aplikasi", opsi, horizontal=True, key="fs_app", label_visibility="collapsed")
    mn, mx = rentang_tanggal(aplikasi)
    c1, c2 = st.columns(2)
    with c1:
        dari = st.date_input("Dari", value=None, min_value=mn, max_value=mx,
                             key="fs_dari", format="DD/MM/YYYY")
    with c2:
        sampai = st.date_input("Sampai", value=None, min_value=mn, max_value=mx,
                               key="fs_sampai", format="DD/MM/YYYY")
    if mn and mx:
        st.caption(f"Data tersedia: {mn.strftime('%d/%m/%Y')} s.d. {mx.strftime('%d/%m/%Y')}")
    if dari and sampai and dari > sampai:
        st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'.")
        return
    df = sentimen_tersaring(aplikasi, dari, sampai)
    if df.empty:
        st.warning("Tidak ada ulasan pada selang waktu ini.")
        return
    pivot = df.pivot(index="aplikasi", columns="label", values="jumlah").fillna(0)
    for k in ["Positif", "Negatif"]:
        if k not in pivot.columns:
            pivot[k] = 0
    pivot["Total"] = pivot["Positif"] + pivot["Negatif"]
    pivot["Pos_pct"] = (pivot["Positif"] / pivot["Total"] * 100).round(1)
    pivot["Neg_pct"] = (pivot["Negatif"] / pivot["Total"] * 100).round(1)
    pivot = pivot.reset_index()

    # Persentase per aplikasi (horizontal bar inline, mirip APK)
    mulai_kartu("Persentase Sentimen per Aplikasi")
    for _, b in pivot.iterrows():
        pos_s = f"{b['Pos_pct']:.1f}%".replace(".", ",")
        neg_s = f"{b['Neg_pct']:.1f}%".replace(".", ",")
        st.markdown(
            f'<div class="bar-label">{b["aplikasi"]}</div>'
            f'<div class="bar-inline">'
            f'<div class="bar-pos" style="width:{b["Pos_pct"]}%;">{pos_s}</div>'
            f'<div class="bar-neg" style="width:{b["Neg_pct"]}%;">{neg_s}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="legend-row">'
        f'<span><span class="legend-dot" style="background:{POS};"></span>Positif</span>'
        f'<span><span class="legend-dot" style="background:{NEG};"></span>Negatif</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    tutup_kartu()

    # Tabel Perbandingan
    mulai_kartu("Tabel Perbandingan")
    tampil = pivot[["aplikasi", "Positif", "Negatif", "Pos_pct"]].copy()
    tampil.columns = ["Aplikasi", "Positif", "Negatif", "% Positif"]
    tampil["Positif"] = tampil["Positif"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    tampil["Negatif"] = tampil["Negatif"].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    tampil["% Positif"] = tampil["% Positif"].map(lambda v: f"{v:.1f}%".replace(".", ","))
    st.table(tampil)
    st.caption("Menghitung seluruh ulasan berdasarkan label hasil pelabelan hybrid (leksikon InSet + rating).")
    tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Performa Algoritma
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    data = ringkasan_global()
    aplikasi = st.radio("Aplikasi", data["aplikasi"], horizontal=True, key="fp_app",
                        label_visibility="collapsed")
    perf = performa_semua()
    if perf.empty:
        st.info("Metrik performa belum tersedia.")
        return
    sub = perf[perf["aplikasi"] == aplikasi].sort_values("model")
    if sub.empty:
        st.warning(f"Tidak ada data performa untuk aplikasi {aplikasi}.")
        return

    # Macro-F1 — bar inline
    mulai_kartu("Macro-F1 (data uji)")
    for _, b in sub.iterrows():
        pct = b["macro_f1"] * 100
        f1_s = f"{b['macro_f1']:.4f}".replace(".", ",")
        st.markdown(
            f'<div class="bar-label">{b["model"]}</div>'
            f'<div class="bar-inline" style="background:#eee;">'
            f'<div style="width:{pct}%; background:{HD}; display:flex; align-items:center; '
            f'justify-content:flex-end; padding:0 0.6rem; color:white; font-weight:700; font-size:0.82rem;">{f1_s}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]["model"]
    st.markdown(
        f'<div style="color:{POS}; font-weight:700; margin-top:0.6rem;">Model terbaik: {terbaik}</div>',
        unsafe_allow_html=True,
    )
    tutup_kartu()

    # Metrik Evaluasi — tabel
    mulai_kartu("Metrik Evaluasi")
    kolom = [
        ("accuracy", "Accuracy"),
        ("precision_pos", "Precision (+)"),
        ("recall_pos", "Recall (+)"),
        ("f1_pos", "F1 (+)"),
        ("macro_f1", "Macro-F1"),
    ]
    tabel = pd.DataFrame({"Metrik": [n for _, n in kolom]})
    for _, baris in sub.iterrows():
        tabel[baris["model"]] = [
            f"{baris[k]:.4f}".replace(".", ",") if pd.notna(baris[k]) else "-"
            for k, _ in kolom
        ]
    st.table(tabel)
    st.caption("Precision, recall, dan F1 dihitung untuk kelas positif. Selisih macro-F1 < 0,01 dianggap setara.")
    tutup_kartu()

    # Confusion Matrix
    mulai_kartu(f"Confusion Matrix - {terbaik}")
    b = sub[sub["model"] == terbaik].iloc[0]
    tp, fn, fp, tn = int(b["tp"]), int(b["fn"]), int(b["fp"]), int(b["tn"])

    def _cell(n: int, dark: bool) -> str:
        warna = HD_DARK if dark else HD_SOFT
        warna_teks = "white" if dark else HD_DARK
        return (
            f'<div style="background:{warna}; color:{warna_teks}; padding:1.1rem; '
            f'text-align:center; font-weight:700; font-size:1.1rem; border-radius:6px;">'
            f'{n:,}</div>'.replace(",", ".")
        )

    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns: auto 1fr 1fr; gap:6px; margin-top:0.4rem;">
          <div></div>
          <div style="text-align:center; font-size:0.85rem; color:{MUTED}; padding:0.3rem;">Prediksi +</div>
          <div style="text-align:center; font-size:0.85rem; color:{MUTED}; padding:0.3rem;">Prediksi -</div>
          <div style="display:flex; align-items:center; font-size:0.85rem; color:{MUTED}; padding:0.3rem 0.6rem 0.3rem 0;">Aktual +</div>
          {_cell(tp, True)}
          {_cell(fn, False)}
          <div style="display:flex; align-items:center; font-size:0.85rem; color:{MUTED}; padding:0.3rem 0.6rem 0.3rem 0;">Aktual -</div>
          {_cell(fp, False)}
          {_cell(tn, True)}
        </div>
        """,
        unsafe_allow_html=True,
    )
    tutup_kartu()


# ---------------------------------------------------------------------------
# Halaman: Admin
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    data = ringkasan_global()

    mulai_kartu("Unggah Data Ulasan")
    st.caption("Kolom wajib: content, score, at. Hanya ulasan yang lebih baru dari data terakhir yang dimuat (maks. 2.000 ulasan).")
    aplikasi = st.radio("Aplikasi", data["aplikasi"], horizontal=True, key="admin_app",
                        label_visibility="collapsed")
    berkas = st.file_uploader("Pilih File", type=["csv", "xlsx"], label_visibility="collapsed")
    label_file = berkas.name if berkas else "Belum ada berkas"
    st.caption(f"📄 {label_file}")
    if st.button("Unggah dan Proses", type="primary", use_container_width=True, disabled=berkas is None):
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
        for i, baris in riwayat.iterrows():
            kol = st.columns([5, 1])
            with kol[0]:
                tgl = baris["waktu"].strftime("%d %b %Y %H:%M") if pd.notna(baris["waktu"]) else "-"
                jml = (
                    f"{int(baris['jumlah_baris']):,} ulasan".replace(",", ".")
                    if pd.notna(baris["jumlah_baris"]) else ""
                )
                status = baris["status"]
                warna_s = NEG if status == "Dibatalkan" else (POS if status == "Diterima" else MUTED)
                st.markdown(
                    f'<div style="font-weight:600; font-size:0.9rem; color:{HD_DARK};">#{baris["id"]} {baris["aplikasi"]} — {baris["berkas"] or "-"}</div>'
                    f'<div style="font-size:0.8rem; color:{MUTED};">{tgl} · {jml} · '
                    f'<span style="color:{warna_s}; font-weight:600;">{status}</span></div>',
                    unsafe_allow_html=True,
                )
            with kol[1]:
                if status != "Dibatalkan":
                    if st.button("Batal", key=f"batal_{baris['id']}"):
                        batalkan_unggahan(int(baris["id"]))
                        ringkasan_global.clear()
                        riwayat_unggahan.clear()
                        st.rerun()
            st.markdown("<hr style='margin:0.4rem 0; border:none; border-top:1px solid #eee;'>", unsafe_allow_html=True)
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
        eksekusi(
            "UPDATE riwayat_pelatihan SET status = 'Dibatalkan' WHERE id = %s",
            (id_unggahan,),
        )
    except Exception as exc:
        st.error(f"Gagal membatalkan: {exc}")


# ---------------------------------------------------------------------------
# Halaman: Login
# ---------------------------------------------------------------------------
def halaman_login() -> None:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="login-title">Analisis Sentimen</div>'
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
    with st.sidebar:
        st.markdown(f"**{user['username']}**  \nPeran: `{user['role']}`")
        if st.button("Keluar", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
        st.divider()
        st.caption("Dashboard Analisis Sentimen")
        st.caption("Universitas Tarumanagara")

    # Pilih halaman via tabs
    if user["role"] == "Admin":
        tab_ring, tab_sent, tab_perf, tab_adm = st.tabs(["Ringkasan", "Sentimen", "Performa", "Admin"])
        with tab_ring:
            page_header("Ringkasan Insight", user["username"])
            halaman_ringkasan()
        with tab_sent:
            page_header("Perbandingan Sentimen", user["username"])
            halaman_sentimen()
        with tab_perf:
            page_header("Performa Algoritma", user["username"])
            halaman_performa()
        with tab_adm:
            page_header("Admin: Unggah Data", user["username"])
            halaman_admin(user)
    else:
        tab_ring, tab_sent, tab_perf = st.tabs(["Ringkasan", "Sentimen", "Performa"])
        with tab_ring:
            page_header("Ringkasan Insight", user["username"])
            halaman_ringkasan()
        with tab_sent:
            page_header("Perbandingan Sentimen", user["username"])
            halaman_sentimen()
        with tab_perf:
            page_header("Performa Algoritma", user["username"])
            halaman_performa()


def main() -> None:
    if "user" not in st.session_state:
        halaman_login()
    else:
        aplikasi_utama()


if __name__ == "__main__":
    main()
