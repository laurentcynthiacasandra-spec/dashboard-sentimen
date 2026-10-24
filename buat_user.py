"""Membuat / mengganti akun.  Contoh:
   python buat_user.py admin  Admin     (akan meminta password)
   python buat_user.py budi   Pengguna
"""
import sys, getpass
from sqlalchemy import select, insert, update
from werkzeug.security import generate_password_hash
import db
db.init_db()
if len(sys.argv) != 3 or sys.argv[2] not in ("Admin", "Pengguna"):
    sys.exit("Pakai: python buat_user.py <username> <Admin|Pengguna>")
u, role = sys.argv[1], sys.argv[2]
pw = getpass.getpass("Password: ")
if len(pw) < 6: sys.exit("Password minimal 6 karakter")
with db.engine.begin() as c:
    ada = c.execute(select(db.users.c.id_user).where(db.users.c.username == u)).first()
    h = generate_password_hash(pw)
    if ada: c.execute(update(db.users).where(db.users.c.username == u).values(password_hash=h, role=role)); print("Akun diperbarui.")
    else: c.execute(insert(db.users).values(username=u, password_hash=h, role=role)); print("Akun dibuat.")
