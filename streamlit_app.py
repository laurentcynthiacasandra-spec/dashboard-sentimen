import os
import io
from datetime import date, datetime

import bcrypt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import psycopg2.extras
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
POS = "#3F8A1E"
NEG = "#D94545"
BG = "#EFEAE8"

st.markdown(
    f"""
    <style>
    .main .block-container {{max-width: 1100px; padding-top: 1rem; padding-bottom: 2rem;}}
    .stTabs [data-baseweb="tab-list"] {{gap: 4px;}}
    .stTabs [data-baseweb="tab"] {{background: {BG}; border-radius: 8px 8px 0 0;}}
    .stTabs [aria-selected="true"] {{background: {HD}; color: white;}}
    .metric-card {{background: white; padding: 1rem; border-radius: 8px; border: 1px solid #ddd;}}
    .metric-label {{color: #666; font-size: 0.85rem; text-transform: uppercase;}}
    .metric-value {{font-size: 2rem; font-weight: bold; color: {HD};}}
    .metric-sub {{color: #666; font-size: 0.9rem;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Koneksi basis data (memanfaatkan Streamlit Secrets)
# ---------------------------------------------------------------------------
def _get_dsn() -> str:
    """Ambil DATABASE_URL dari Streamlit Secrets atau env."""
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.environ["DATABASE_URL"]


@st.cache_resource
def get_conn():
    """Koneksi tunggal ke PostgreSQL Neon."""
    return psycopg2.connect(_get_dsn(), sslmode="require")


def kueri(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Jalankan kueri SELECT dan kembalikan DataFrame."""
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
    """Jalankan kueri INSERT/UPDATE/DELETE."""
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
    """Verifikasi kredensial pengguna, kembalikan dict user atau None."""
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
    """Daftarkan akun berperan Pengguna."""
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
def model_terbaru_id() -> int:
    """Ambil id_model terkecil (model yang disimpan)."""
    df = kueri("SELECT MIN(id_model) AS id_min FROM fact_sentimen")
    return int(df.iloc[0]["id_min"]) if not df.empty else 1


@st.cache_data(ttl=300, show_spinner=False)
def ringkasan_global() -> dict:
    """Ambil total ulasan, rata-rata positif, dan jumlah aplikasi."""
    idm = model_terbaru_id()
    df = kueri(
        """
        SELECT a.nama AS aplikasi, s.nama AS label, COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        WHERE f.id_model = %s
        GROUP BY a.nama, s.nama
        ORDER BY a.nama, s.nama
        """,
        (idm,),
    )
    total = int(df["jumlah"].sum())
    positif = int(df[df["label"].str.lower() == "positif"]["jumlah"].sum())
    pos_pct = (positif / total * 100) if total else 0.0
    aplikasi = sorted(df["aplikasi"].unique())
    return {
        "total": total,
        "positif_pct": pos_pct,
        "jumlah_aplikasi": len(aplikasi),
        "aplikasi": aplikasi,
        "rincian": df,
    }


@st.cache_data(ttl=300, show_spinner=False)
def performa_semua() -> pd.DataFrame:
    """Ambil metrik performa model per aplikasi."""
    try:
        return kueri(
            """
            SELECT a.nama AS aplikasi,
                   m.nama_model AS model,
                   m.accuracy, m.precision_pos, m.recall_pos, m.f1_pos,
                   m.precision_neg, m.recall_neg, m.f1_neg,
                   m.macro_f1, m.waktu_latih,
                   m.tp, m.fp, m.tn, m.fn
            FROM dim_model m
            JOIN dim_aplikasi a ON a.id_aplikasi = m.id_aplikasi
            ORDER BY a.nama, m.nama_model
            """
        )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def rentang_tanggal(aplikasi: str) -> tuple[date, date]:
    """Ambil rentang tanggal data untuk aplikasi tertentu."""
    idm = model_terbaru_id()
    if aplikasi == "Semua":
        sql = """
            SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx
            FROM fact_sentimen f
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE f.id_model = %s
        """
        df = kueri(sql, (idm,))
    else:
        sql = """
            SELECT MIN(w.tanggal) AS mn, MAX(w.tanggal) AS mx
            FROM fact_sentimen f
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            WHERE f.id_model = %s AND a.nama = %s
        """
        df = kueri(sql, (idm, aplikasi))
    mn, mx = df.iloc[0]["mn"], df.iloc[0]["mx"]
    return mn, mx


@st.cache_data(ttl=300, show_spinner=False)
def sentimen_tersaring(aplikasi: str, dari: date | None, sampai: date | None) -> pd.DataFrame:
    """Hitung sentimen per aplikasi, boleh disaring selang waktu."""
    idm = model_terbaru_id()
    kondisi_app = "" if aplikasi == "Semua" else "AND a.nama = %s"
    param_app: tuple = () if aplikasi == "Semua" else (aplikasi,)
    if dari and sampai:
        sql = f"""
            SELECT a.nama AS aplikasi, s.nama AS label, COUNT(*) AS jumlah
            FROM fact_sentimen f
            JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
            JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
            JOIN dim_waktu w ON w.id_waktu = f.id_waktu
            WHERE f.id_model = %s AND w.tanggal BETWEEN %s AND %s {kondisi_app}
            GROUP BY a.nama, s.nama
            ORDER BY a.nama, s.nama
        """
        return kueri(sql, (idm, dari, sampai) + param_app)
    sql = f"""
        SELECT a.nama AS aplikasi, s.nama AS label, COUNT(*) AS jumlah
        FROM fact_sentimen f
        JOIN dim_aplikasi a ON a.id_aplikasi = f.id_aplikasi
        JOIN dim_sentimen s ON s.id_sentimen = f.id_sentimen
        WHERE f.id_model = %s {kondisi_app}
        GROUP BY a.nama, s.nama
        ORDER BY a.nama, s.nama
    """
    return kueri(sql, (idm,) + param_app)


@st.cache_data(ttl=60, show_spinner=False)
def riwayat_unggahan() -> pd.DataFrame:
    """Ambil riwayat unggahan Admin."""
    try:
        return kueri(
            """
            SELECT r.id, r.waktu, u.username, a.nama AS aplikasi,
                   r.berkas, r.jumlah_baris, r.status, r.catatan
            FROM riwayat_pelatihan r
            JOIN users u ON u.id_user = r.id_user
            JOIN dim_aplikasi a ON a.id_aplikasi = r.id_aplikasi
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
            {f'<div class="metric-sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def grafik_distribusi(data: dict) -> None:
    rincian = data["rincian"]
    pos_total = int(rincian[rincian["label"].str.lower() == "positif"]["jumlah"].sum())
    neg_total = int(rincian[rincian["label"].str.lower() == "negatif"]["jumlah"].sum())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Positif", "Negatif"],
                values=[pos_total, neg_total],
                hole=0.5,
                marker=dict(colors=[POS, NEG]),
                textinfo="label+percent",
                textfont=dict(size=14),
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        height=320,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Halaman: Ringkasan Insight Utama
# ---------------------------------------------------------------------------
def halaman_ringkasan() -> None:
    st.header("Ringkasan Insight Utama")
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
        kartu_metrik("Model Terbaik", "SVM (kernel linear)")

    st.markdown("### Distribusi Sentimen")
    grafik_distribusi(data)

    st.markdown("### Insight Utama")
    # Hitung aplikasi dengan sentimen positif tertinggi
    rincian = data["rincian"]
    pos_app = (
        rincian[rincian["label"].str.lower() == "positif"]
        .merge(
            rincian.groupby("aplikasi")["jumlah"].sum().reset_index().rename(
                columns={"jumlah": "total_app"}
            ),
            on="aplikasi",
        )
    )
    pos_app["pct"] = pos_app["jumlah"] / pos_app["total_app"] * 100
    terbaik = pos_app.sort_values("pct", ascending=False).iloc[0]
    data_terakhir = kueri(
        "SELECT MAX(w.tanggal) AS mx FROM fact_sentimen f JOIN dim_waktu w ON w.id_waktu = f.id_waktu"
    ).iloc[0]["mx"]
    st.markdown(
        f"""
        - **{terbaik['aplikasi']}** memiliki sentimen positif tertinggi ({terbaik['pct']:.1f}%).
        - Pada ketiga aplikasi, model SVM memberikan macro-F1 yang lebih tinggi dibanding Naive Bayes.
        - Data terbaru: **{data_terakhir.strftime('%d %B %Y')}**.
        """
    )


# ---------------------------------------------------------------------------
# Halaman: Perbandingan Sentimen
# ---------------------------------------------------------------------------
def halaman_sentimen() -> None:
    st.header("Perbandingan Sentimen")
    data = ringkasan_global()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        aplikasi = st.selectbox(
            "Aplikasi",
            ["Semua"] + data["aplikasi"],
            index=0,
            key="filter_sentimen_app",
        )
    mn, mx = rentang_tanggal(aplikasi)
    with col2:
        dari = st.date_input(
            "Dari",
            value=None,
            min_value=mn,
            max_value=mx,
            key="filter_sentimen_dari",
            format="DD/MM/YYYY",
        )
    with col3:
        sampai = st.date_input(
            "Sampai",
            value=None,
            min_value=mn,
            max_value=mx,
            key="filter_sentimen_sampai",
            format="DD/MM/YYYY",
        )
    st.caption(
        f"Data tersedia pada rentang **{mn.strftime('%d %b %Y')} – {mx.strftime('%d %b %Y')}**."
    )

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

    st.subheader("Persentase Sentimen per Aplikasi")
    melt = pivot.reset_index().melt(
        id_vars="aplikasi",
        value_vars=["Positif %", "Negatif %"],
        var_name="Sentimen",
        value_name="Persentase",
    )
    melt["Sentimen"] = melt["Sentimen"].str.replace(" %", "")
    fig = px.bar(
        melt,
        x="Persentase",
        y="aplikasi",
        color="Sentimen",
        orientation="h",
        color_discrete_map={"Positif": POS, "Negatif": NEG},
        text="Persentase",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
    fig.update_layout(
        xaxis=dict(range=[0, 100], title=""),
        yaxis=dict(title=""),
        barmode="stack",
        height=260,
        margin=dict(l=10, r=10, t=30, b=10),
        legend_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tabel Perbandingan")
    tampil = pivot.reset_index()[["aplikasi", "Positif", "Negatif", "Total"]].copy()
    tampil.columns = ["Aplikasi", "Positif", "Negatif", "Total"]
    for c in ["Positif", "Negatif", "Total"]:
        tampil[c] = tampil[c].astype(int).map(lambda v: f"{v:,}".replace(",", "."))
    st.table(tampil)


# ---------------------------------------------------------------------------
# Halaman: Performa Algoritma
# ---------------------------------------------------------------------------
def halaman_performa() -> None:
    st.header("Perbandingan Performa Algoritma")
    data = ringkasan_global()
    aplikasi = st.selectbox("Aplikasi", data["aplikasi"], key="filter_performa_app")
    perf = performa_semua()
    if perf.empty:
        st.info(
            "Metrik performa belum tersedia. Pastikan tabel dim_model telah terisi hasil evaluasi."
        )
        return
    sub = perf[perf["aplikasi"] == aplikasi].sort_values("model")
    if sub.empty:
        st.warning(f"Tidak ada data performa untuk aplikasi {aplikasi}.")
        return

    st.subheader("Macro-F1 (data uji)")
    fig = px.bar(
        sub,
        x="macro_f1",
        y="model",
        orientation="h",
        color="model",
        color_discrete_map={"Naive Bayes": "#2A79D6", "SVM": "#1B4F8A"},
        text="macro_f1",
    )
    fig.update_traces(texttemplate="%{text:.4f}", textposition="outside")
    fig.update_layout(
        xaxis=dict(range=[0, 1], title=""),
        yaxis=dict(title=""),
        showlegend=False,
        height=220,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    terbaik = sub.sort_values("macro_f1", ascending=False).iloc[0]["model"]
    st.success(f"Model terbaik untuk {aplikasi}: **{terbaik}**")

    st.subheader("Metrik Evaluasi")
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

    st.subheader(f"Confusion Matrix ({terbaik})")
    bar_terbaik = sub[sub["model"] == terbaik].iloc[0]
    if pd.notna(bar_terbaik.get("tp")):
        cm_df = pd.DataFrame(
            [
                ["Aktual Positif", int(bar_terbaik["tp"]), int(bar_terbaik["fn"])],
                ["Aktual Negatif", int(bar_terbaik["fp"]), int(bar_terbaik["tn"])],
            ],
            columns=["", "Prediksi Positif", "Prediksi Negatif"],
        )
        st.table(cm_df)
    else:
        st.caption("Confusion matrix belum tersedia pada tabel dim_model.")


# ---------------------------------------------------------------------------
# Halaman: Admin — Unggah dan Riwayat
# ---------------------------------------------------------------------------
def halaman_admin(user: dict) -> None:
    st.header("Halaman Admin")
    data = ringkasan_global()

    st.subheader("Unggah Data Ulasan Baru")
    aplikasi = st.selectbox("Aplikasi", data["aplikasi"], key="admin_app")
    berkas = st.file_uploader(
        "Berkas ulasan (.csv atau .xlsx, kolom: content, score, at)",
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

    st.divider()
    st.subheader("Riwayat Unggahan")
    riwayat = riwayat_unggahan()
    if riwayat.empty:
        st.info("Belum ada unggahan.")
        return
    for _, baris in riwayat.iterrows():
        kolom = st.columns([2, 2, 2, 3, 2, 1])
        kolom[0].write(baris["waktu"].strftime("%d %b %Y %H:%M") if pd.notna(baris["waktu"]) else "-")
        kolom[1].write(baris["aplikasi"])
        kolom[2].write(baris["username"])
        kolom[3].write(baris["berkas"] or "-")
        kolom[4].write(
            f"{int(baris['jumlah_baris']):,} ulasan".replace(",", ".")
            if pd.notna(baris["jumlah_baris"])
            else "-"
        )
        if baris["status"] == "Diterima":
            if kolom[5].button("Batal", key=f"batal_{baris['id']}"):
                batalkan_unggahan(int(baris["id"]))
                ringkasan_global.clear()
                riwayat_unggahan.clear()
                st.rerun()
        else:
            kolom[5].caption(baris["status"])


def proses_unggahan(user: dict, aplikasi: str, berkas) -> None:
    """Validasi berkas unggahan Admin dan simpan sebagai pending.

    Catatan: logika pelabelan hybrid dan prediksi model dijalankan terpisah
    oleh skrip pipeline Python pada perangkat peneliti. Fungsi ini hanya
    menerima dan memvalidasi berkas serta mencatat ke riwayat_pelatihan.
    """
    try:
        if berkas.name.lower().endswith(".csv"):
            df = pd.read_csv(berkas)
        else:
            df = pd.read_excel(berkas)
    except Exception as exc:
        st.error(f"Berkas tidak dapat dibaca: {exc}")
        return
    wajib = {"content", "score", "at"}
    hilang = wajib - set(df.columns.str.lower())
    if hilang:
        st.error(f"Kolom wajib tidak lengkap: {', '.join(sorted(hilang))}.")
        return
    if len(df) > 2000:
        st.error(f"Jumlah baris ({len(df)}) melebihi batas 2.000 ulasan per unggahan.")
        return
    try:
        id_app_df = kueri(
            "SELECT id_aplikasi FROM dim_aplikasi WHERE nama = %s", (aplikasi,)
        )
        id_app = int(id_app_df.iloc[0]["id_aplikasi"])
        eksekusi(
            """
            INSERT INTO riwayat_pelatihan (waktu, id_user, id_aplikasi, berkas, jumlah_baris, status, catatan)
            VALUES (NOW(), %s, %s, %s, %s, 'Pending', %s)
            """,
            (
                user["id_user"],
                id_app,
                berkas.name,
                len(df),
                f"Menunggu pemrosesan oleh skrip pipeline",
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
    st.markdown(
        f"<h1 style='color:{HD};text-align:center;margin-top:2rem;'>Analisis Sentimen</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#666;'>Instagram · TikTok · X</p>",
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
