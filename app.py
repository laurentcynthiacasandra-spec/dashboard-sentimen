"""Dashboard Analisis Sentimen (web app) - Flask + PostgreSQL.
Jalankan:  python app.py      lalu buka http://localhost:5000
"""
import os, re, time, secrets, datetime, functools
from flask import Flask, request, session, redirect, url_for, render_template, jsonify, abort
from sqlalchemy import select, func, insert, update, delete, and_
from werkzeug.security import check_password_hash, generate_password_hash
import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "kunci-lokal-hanya-untuk-uji-coba"
if not os.environ.get("SECRET_KEY") and os.environ.get("PORT"):  # berjalan di hosting tanpa SECRET_KEY: jangan pakai kunci bawaan
    app.secret_key = secrets.token_hex(32); print("PERINGATAN: SECRET_KEY belum diisi; sesi login akan hilang saat server restart.")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.environ.get("HTTPS", "") == "1")
BOLEH_DAFTAR = os.environ.get("BOLEH_DAFTAR", "1") == "1"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads"); os.makedirs(UPLOAD_DIR, exist_ok=True)
da, dw, dm, ds, fs, fe, rl = db.dim_aplikasi, db.dim_waktu, db.dim_model, db.dim_sentimen, db.fact_sentimen, db.fact_evaluasi, db.ringkasan_label

# ---------------------------------------------------------------- autentikasi & otorisasi
def login_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        if "user" not in session:
            if request.path.startswith("/api/"): return jsonify(error="Belum login"), 401
            return redirect(url_for("login"))
        return f(*a, **k)
    return w

def admin_required(f):
    @functools.wraps(f)
    @login_required
    def w(*a, **k):
        if session.get("role") != "Admin":
            if request.path.startswith("/api/"): return jsonify(error="Akses ditolak: hanya untuk Admin"), 403
            return render_template("ditolak.html"), 403
        return f(*a, **k)
    return w

@app.context_processor
def ctx(): return dict(user=session.get("user"), role=session.get("role"))

GAGAL = {}                      # (ip, username) -> [jumlah gagal, waktu gagal pertama]; dipakai untuk membatasi tebak-tebakan password
BATAS_GAGAL, JEDA = 5, 300      # 5 kali gagal -> terkunci 5 menit
def _ip(): return (request.headers.get("X-Forwarded-For", request.remote_addr) or "?").split(",")[0].strip()
def _terkunci(k):
    g = GAGAL.get(k)
    if not g: return 0
    sisa = JEDA - (time.time() - g[1])
    if sisa <= 0: GAGAL.pop(k, None); return 0
    return int(sisa) + 1 if g[0] >= BATAS_GAGAL else 0

@app.route("/login", methods=["GET", "POST"])
def login():
    err = None; info = request.args.get("info")
    if request.method == "POST":
        u, p = request.form.get("username", "").strip(), request.form.get("password", "")
        k = (_ip(), u.lower()); sisa = _terkunci(k)
        if sisa: return render_template("login.html", err=f"Terlalu banyak percobaan gagal. Coba lagi dalam {sisa // 60 + 1} menit.", daftar=BOLEH_DAFTAR), 429
        with db.engine.connect() as c:
            r = c.execute(select(db.users).where(db.users.c.username == u)).first()
        if r and check_password_hash(r.password_hash, p):
            GAGAL.pop(k, None)
            session.clear(); session["user"], session["role"], session["uid"] = r.username, r.role, r.id_user
            return redirect(url_for("ringkasan"))
        g = GAGAL.setdefault(k, [0, time.time()]); g[0] += 1
        err = "Username atau password salah."
    return render_template("login.html", err=err, info=info, daftar=BOLEH_DAFTAR)

@app.route("/daftar", methods=["GET", "POST"])
def daftar():
    """Pendaftaran mandiri: akun yang dibuat selalu berperan Pengguna (Admin hanya dibuat oleh Admin)."""
    if not BOLEH_DAFTAR: abort(404)
    err = None; u = ""
    if request.method == "POST":
        u, p, p2 = request.form.get("username", "").strip(), request.form.get("password", ""), request.form.get("password2", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", u): err = "Username 3-30 karakter: huruf, angka, titik, garis bawah, atau strip."
        elif len(p) < 8: err = "Password minimal 8 karakter."
        elif p != p2: err = "Konfirmasi password tidak sama."
        else:
            with db.engine.begin() as c:
                if c.execute(select(db.users.c.id_user).where(func.lower(db.users.c.username) == u.lower())).first(): err = "Username sudah dipakai."
                else:
                    c.execute(insert(db.users).values(username=u, password_hash=generate_password_hash(p), role="Pengguna"))
                    return redirect(url_for("login", info="Akun berhasil dibuat. Silakan masuk."))
    return render_template("daftar.html", err=err, u=u)

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("login"))

# ---------------------------------------------------------------- halaman
@app.route("/")
def index(): return redirect(url_for("ringkasan") if "user" in session else url_for("login"))
@app.route("/ringkasan")
@login_required
def ringkasan(): return render_template("ringkasan.html", aktif="ringkasan")
@app.route("/sentimen")
@login_required
def sentimen(): return render_template("sentimen.html", aktif="sentimen")
@app.route("/performa")
@login_required
def performa(): return render_template("performa.html", aktif="performa")
@app.route("/admin")
@admin_required
def admin(): return render_template("admin.html", aktif="admin")

# ---------------------------------------------------------------- API
def _apps(c): return [dict(id=r.id_aplikasi, nama=r.nama_aplikasi) for r in c.execute(select(da).order_by(da.c.id_aplikasi))]
def _models(c): return [dict(id=r.id_model, nama=r.nama_model, pembanding=bool(r.pembanding)) for r in c.execute(select(dm).order_by(dm.c.id_model))]

@app.route("/api/meta")
@login_required
def api_meta():
    with db.engine.connect() as c:
        mn, mx = c.execute(select(func.min(dw.c.tanggal), func.max(dw.c.tanggal))).first()
        tahun = sorted(r[0] for r in c.execute(select(dw.c.tahun).distinct()))
        return jsonify(aplikasi=_apps(c), model=_models(c), tanggal_min=str(mn), tanggal_max=str(mx), tahun=tahun)

def _rentang(): return request.args.get("dari") or "0001-01-01", request.args.get("sampai") or "9999-12-31"

@app.route("/api/ringkasan")
@login_required
def api_ringkasan():
    with db.engine.connect() as c:
        apps = {a["id"]: a["nama"] for a in _apps(c)}
        rows = c.execute(select(rl)).all()
        total = sum(r.data_dipakai for r in rows); pos = sum(r.positif for r in rows); neg = sum(r.negatif for r in rows)
        per_app = [dict(aplikasi=apps[r.id_aplikasi], positif=r.positif, negatif=r.negatif, total=r.data_dipakai,
                        persen_positif=round(r.positif / r.data_dipakai * 100, 1), sejalan=r.sejalan_persen) for r in rows]
        best = []
        for r in c.execute(select(fe, dm.c.nama_model).join(dm, dm.c.id_model == fe.c.id_model).where(fe.c.terbaik == True)):  # noqa
            best.append(dict(aplikasi=apps[r.id_aplikasi], model=r.nama_model, macro_f1=round(r.macro_f1, 4)))
        mx = c.execute(select(func.max(dw.c.tanggal))).scalar()
    insight = []
    if per_app:
        t = max(per_app, key=lambda a: a["persen_positif"]); b = min(per_app, key=lambda a: a["persen_positif"])
        insight.append(f"{t['aplikasi']} memiliki proporsi sentimen positif tertinggi ({t['persen_positif']}%), sedangkan {b['aplikasi']} terendah ({b['persen_positif']}%).")
        for x in best: insight.append(f"Pada {x['aplikasi']}, model terbaik adalah {x['model']} (macro-F1 {x['macro_f1']}).")
        lo = min(per_app, key=lambda a: a["sejalan"])
        insight.append(f"Kesesuaian rating dengan skor leksikon hanya {lo['sejalan']}% pada {lo['aplikasi']}, sehingga klasifikasi berbasis teks tetap diperlukan.")
    return jsonify(total=total, persen_positif=round(pos / total * 100, 1) if total else 0, positif=pos, negatif=neg,
                   per_app=per_app, terbaik=best, tanggal_terakhir=str(mx), insight=insight)

@app.route("/api/sentimen")
@login_required
def api_sentimen():
    """Distribusi & tren sentimen. sumber=aktual (hasil pelabelan hybrid) atau prediksi (data uji, model terpilih)."""
    app_id = request.args.get("app", type=int); sumber = request.args.get("sumber", "aktual")
    model_id = request.args.get("model", 1, type=int); dari, sampai = _rentang()
    kolom = fs.c.id_sentimen if sumber == "aktual" else fs.c.id_sentimen_prediksi
    cond = [fs.c.id_model == model_id, dw.c.tanggal >= datetime.date.fromisoformat(dari) if dari[0] != "0" else True,
            dw.c.tanggal <= datetime.date.fromisoformat(sampai) if sampai[0] != "9" else True]
    if sumber == "prediksi": cond.append(fs.c.data_uji == True)  # noqa
    if app_id: cond.append(fs.c.id_aplikasi == app_id)
    cond = [x for x in cond if x is not True]
    with db.engine.connect() as c:
        apps = {a["id"]: a["nama"] for a in _apps(c)}
        q = select(fs.c.id_aplikasi, kolom.label("s"), func.count().label("n")).join(dw, dw.c.id_waktu == fs.c.id_waktu).where(and_(*cond)).group_by(fs.c.id_aplikasi, kolom)
        dist = {}
        for r in c.execute(q): dist.setdefault(apps[r.id_aplikasi], {1: 0, 2: 0})[r.s] = r.n
        q2 = select(fs.c.id_aplikasi, dw.c.tahun, dw.c.bulan, kolom.label("s"), func.count().label("n")).join(dw, dw.c.id_waktu == fs.c.id_waktu).where(and_(*cond)).group_by(fs.c.id_aplikasi, dw.c.tahun, dw.c.bulan, kolom)
        tren = {}
        for r in c.execute(q2): tren.setdefault(apps[r.id_aplikasi], {}).setdefault(f"{r.tahun}-{r.bulan:02d}", {1: 0, 2: 0})[r.s] = r.n
    out = [dict(aplikasi=k, positif=v[1], negatif=v[2], persen_positif=round(v[1] / max(v[1] + v[2], 1) * 100, 1)) for k, v in dist.items()]
    t = {k: [dict(bulan=b, positif=v[1], negatif=v[2]) for b, v in sorted(d.items())] for k, d in tren.items()}
    return jsonify(distribusi=out, tren=t)

@app.route("/api/performa")
@login_required
def api_performa():
    app_id = request.args.get("app", type=int)
    with db.engine.connect() as c:
        apps = {a["id"]: a["nama"] for a in _apps(c)}
        q = select(fe, dm.c.nama_model, dm.c.pembanding).join(dm, dm.c.id_model == fe.c.id_model).order_by(fe.c.id_aplikasi, fe.c.id_model)
        if app_id: q = q.where(fe.c.id_aplikasi == app_id)
        rows = [dict(aplikasi=apps[r.id_aplikasi], id_aplikasi=r.id_aplikasi, model=r.nama_model, id_model=r.id_model, pembanding=bool(r.pembanding),
                     accuracy=r.accuracy, precision=r.precision_pos, recall=r.recall_pos, f1=r.f1_pos, macro_f1=r.macro_f1, waktu=r.waktu_latih,
                     terbaik=bool(r.terbaik), n_latih=r.n_latih, n_uji=r.n_uji, tp=r.tp, fn=r.fn, fp=r.fp, tn=r.tn) for r in c.execute(q)]
    rek = []
    for aid in sorted({r["id_aplikasi"] for r in rows}):
        utama = sorted([r for r in rows if r["id_aplikasi"] == aid and not r["pembanding"]], key=lambda r: -r["macro_f1"])
        if len(utama) >= 2:
            sel = utama[0]["macro_f1"] - utama[1]["macro_f1"]
            txt = (f"Selisih macro-F1 {sel:.4f} (< 0,01): kedua model dianggap setara." if sel < 0.01 else
                   f"{utama[0]['model']} lebih baik (macro-F1 {utama[0]['macro_f1']:.4f} vs {utama[1]['macro_f1']:.4f}, selisih {sel:.4f}).")
            rek.append(dict(aplikasi=utama[0]["aplikasi"], rekomendasi=utama[0]["model"] if sel >= 0.01 else "Setara", keterangan=txt))
    return jsonify(metrik=rows, rekomendasi=rek)

@app.route("/api/admin/riwayat")
@admin_required
def api_riwayat():
    with db.engine.connect() as c:
        rs = c.execute(select(db.riwayat_pelatihan, db.users.c.username).join(db.users, db.users.c.id_user == db.riwayat_pelatihan.c.id_user, isouter=True)
                       .order_by(db.riwayat_pelatihan.c.id.desc()).limit(20)).all()
    return jsonify([dict(waktu=r.waktu.strftime("%d %b %Y %H:%M"), user=r.username, aplikasi=r.aplikasi, berkas=r.berkas,
                         baris=r.jumlah_baris, status=r.status, catatan=r.catatan) for r in rs])

# ---------------------------------------------------------------- kelola pengguna (Admin)
import re
ROLES = ("Admin", "Pengguna")
def _cek_user(username, password, role, wajib_password=True):
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,50}", username or ""): return "Username 3-50 karakter: huruf, angka, titik, garis bawah, atau strip."
    if role not in ROLES: return "Peran harus Admin atau Pengguna."
    if (wajib_password or password) and len(password or "") < 6: return "Password minimal 6 karakter."
    return None

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_users():
    with db.engine.connect() as c:
        rs = c.execute(select(db.users).order_by(db.users.c.id_user)).all()
    return jsonify([dict(id=r.id_user, username=r.username, role=r.role, saya=(r.id_user == session["uid"])) for r in rs])

@app.route("/api/admin/users", methods=["POST"])
@admin_required
def api_users_tambah():
    j = request.get_json(silent=True) or {}
    u, p, role = (j.get("username") or "").strip(), j.get("password") or "", j.get("role") or ""
    err = _cek_user(u, p, role)
    if err: return jsonify(error=err), 400
    with db.engine.begin() as c:
        if c.execute(select(db.users.c.id_user).where(db.users.c.username == u)).first():
            return jsonify(error="Username sudah dipakai."), 409
        c.execute(insert(db.users).values(username=u, password_hash=generate_password_hash(p), role=role))
    return jsonify(ok=True, pesan=f"Akun {u} ({role}) dibuat.")

@app.route("/api/admin/users/<int:uid>", methods=["PUT"])
@admin_required
def api_users_ubah(uid):
    """Ubah password dan/atau peran."""
    j = request.get_json(silent=True) or {}
    p, role = j.get("password") or "", j.get("role")
    with db.engine.begin() as c:
        r = c.execute(select(db.users).where(db.users.c.id_user == uid)).first()
        if not r: return jsonify(error="Akun tidak ditemukan."), 404
        role = role or r.role
        err = _cek_user(r.username, p, role, wajib_password=False)
        if err: return jsonify(error=err), 400
        if r.role == "Admin" and role != "Admin":
            n = c.execute(select(func.count()).select_from(db.users).where(db.users.c.role == "Admin")).scalar()
            if n <= 1: return jsonify(error="Tidak bisa menurunkan Admin terakhir."), 400
        vals = {"role": role}
        if p: vals["password_hash"] = generate_password_hash(p)
        c.execute(update(db.users).where(db.users.c.id_user == uid).values(**vals))
    if uid == session["uid"]: session["role"] = role
    return jsonify(ok=True, pesan=f"Akun {r.username} diperbarui.")

@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def api_users_hapus(uid):
    if uid == session["uid"]: return jsonify(error="Tidak bisa menghapus akun yang sedang dipakai."), 400
    with db.engine.begin() as c:
        r = c.execute(select(db.users).where(db.users.c.id_user == uid)).first()
        if not r: return jsonify(error="Akun tidak ditemukan."), 404
        if r.role == "Admin" and c.execute(select(func.count()).select_from(db.users).where(db.users.c.role == "Admin")).scalar() <= 1:
            return jsonify(error="Tidak bisa menghapus Admin terakhir."), 400
        c.execute(update(db.riwayat_pelatihan).where(db.riwayat_pelatihan.c.id_user == uid).values(id_user=None))
        c.execute(delete(db.users).where(db.users.c.id_user == uid))
    return jsonify(ok=True, pesan=f"Akun {r.username} dihapus.")

KOLOM_WAJIB = {"content", "score", "at"}
@app.route("/api/admin/upload", methods=["POST"])
@admin_required
def api_upload():
    """Validasi berkas ulasan baru. Pelatihan ulang penuh dijalankan oleh pipeline (lihat README, tahap berikutnya)."""
    import pandas as pd
    f = request.files.get("berkas"); aplikasi = request.form.get("aplikasi", "")
    def catat(status, n=0, cat=""):
        with db.engine.begin() as c:
            c.execute(insert(db.riwayat_pelatihan).values(waktu=datetime.datetime.now(), id_user=session["uid"], aplikasi=aplikasi,
                      berkas=(f.filename if f else None), jumlah_baris=n, status=status, catatan=cat))
    if not f or not f.filename: return jsonify(error="Pilih berkas terlebih dahulu."), 400
    if not f.filename.lower().endswith((".xlsx", ".csv")):
        catat("Ditolak", 0, "Format berkas bukan .xlsx/.csv"); return jsonify(error="Format berkas harus .xlsx atau .csv."), 400
    try:
        df = pd.read_csv(f) if f.filename.lower().endswith(".csv") else pd.read_excel(f)
    except Exception as e:
        catat("Ditolak", 0, "Berkas tidak dapat dibaca"); return jsonify(error="Berkas tidak dapat dibaca."), 400
    kurang = KOLOM_WAJIB - set(df.columns)
    if kurang:
        catat("Ditolak", len(df), "Kolom kurang: " + ", ".join(sorted(kurang)))
        return jsonify(error="Kolom wajib tidak ditemukan: " + ", ".join(sorted(kurang))), 400
    if not aplikasi: return jsonify(error="Pilih aplikasi target."), 400
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    df.to_csv(os.path.join(UPLOAD_DIR, f"{aplikasi}_{ts}.csv"), index=False)
    catat("Diterima", len(df), "Menunggu pemrosesan pipeline")
    return jsonify(ok=True, pesan=f"{len(df)} baris diterima dan disimpan. Langkah pelatihan ulang dijalankan melalui pipeline.")

def siapkan():
    """Buat tabel; bila belum ada akun dan ADMIN_PASSWORD diisi (mis. di hosting), buat Admin pertama."""
    db.init_db()
    pw = os.environ.get("ADMIN_PASSWORD")
    if pw:
        with db.engine.begin() as c:
            if not c.execute(select(db.users.c.id_user)).first():
                c.execute(insert(db.users).values(username=os.environ.get("ADMIN_USER", "admin"), password_hash=generate_password_hash(pw), role="Admin"))
                print("Admin pertama dibuat.")
if os.environ.get("PORT"): siapkan()   # dijalankan oleh gunicorn di hosting

if __name__ == "__main__":
    db.init_db()
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)), debug=False)
