# -*- coding: utf-8 -*-
"""Decrypt the local WhatsApp Desktop (WebView2) SQLite databases on Windows.

Runs entirely in the current user's own security context (DPAPI-NG unwraps for
the logged-in user), on a snapshot COPY of the live files. It never modifies the
live WhatsApp store and never sends anything anywhere.

Technique (reverse-engineered; see references in SKILL.md): ODUID from clipc.dll,
staticKey protected via DPAPI-NG NCryptProtectSecret to seed session.db, clientKey
carved from session.db-wal, PBKDF2+AES-CBC to derive the nativeSettings key, then
per-type keys (1 -> genericStorage/messages, 2 -> contacts et al.) decrypt the
AES-OFB page-encrypted databases.

Usage:
  uv run --with cryptography python wa_decrypt.py [OUTPUT_DIR]

OUTPUT_DIR defaults to %LOCALAPPDATA%\\Temp\\wa-decrypted. The output holds every
message you have; treat it as sensitive. Nothing here is committed to git.
"""
import ctypes, struct, hashlib, sys, os, glob, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wa_store
from ctypes import wintypes, c_void_p, byref, POINTER, c_int, c_uint, create_string_buffer
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding

STATIC = bytes.fromhex("23a7f19c11e5bd784235c96f85d24913")
SALT = bytes.fromhex("6300760031006700310067007600")  # "cv1g1gv" UTF-16LE
ITER = 10000
PAGE = 4096
PKG_GLOB = r"*WhatsAppDesktop*"


def oduid():
    clipc = ctypes.WinDLL("clipc.dll")
    f = clipc.GetOfflineDeviceUniqueID
    f.argtypes = [c_uint, ctypes.c_char_p, POINTER(c_uint), POINTER(c_uint), ctypes.c_char_p, c_uint, c_uint]
    f.restype = c_int
    method = c_uint(0); cb = c_uint(32); buf = create_string_buffer(32)
    if f(c_uint(len(SALT)), SALT, byref(method), byref(cb), buf, 0, 0) < 0:
        raise OSError("GetOfflineDeviceUniqueID failed")
    return bytes(buf.raw[:32])


def session_secret():
    ncrypt = ctypes.WinDLL("ncrypt.dll")
    create = ncrypt.NCryptCreateProtectionDescriptor
    create.argtypes = [wintypes.LPCWSTR, c_uint, POINTER(c_void_p)]; create.restype = c_int
    protect = ncrypt.NCryptProtectSecret
    protect.argtypes = [c_void_p, c_uint, ctypes.c_char_p, c_int, c_void_p, c_void_p, POINTER(c_void_p), POINTER(c_int)]
    protect.restype = c_int
    h = c_void_p()
    if create("LOCAL=user", 0, byref(h)) != 0:
        raise OSError("NCryptCreateProtectionDescriptor failed")
    ptr = c_void_p(); size = c_int(0)
    if protect(h, 0, STATIC, len(STATIC), None, None, byref(ptr), byref(size)) != 0:
        raise OSError("NCryptProtectSecret failed")
    return ctypes.string_at(ptr, size.value)[:32]


def _iv(page_no, page):
    return struct.pack("<i", page_no) + bytes(page[-12:])


def dec_db(key, data):
    out = bytearray()
    for i in range(0, len(data), PAGE):
        page = data[i:i + PAGE]
        if len(page) < PAGE:
            out += page; break
        c = Cipher(algorithms.AES(key), modes.OFB(_iv(i // PAGE + 1, page))).decryptor()
        out += c.update(bytes(page)) + c.finalize()
    out[0x10:0x18] = data[0x10:0x18]  # SQLite header page-size/reserved bytes stay plaintext
    return bytes(out)


def dec_wal(key, data):
    H, PH = 32, 24
    out = bytearray(data[:H]); i = H
    while i + PH + PAGE <= len(data):
        ph = data[i:i + PH]; page = data[i + PH:i + PH + PAGE]
        idx = struct.unpack(">i", ph[:4])[0]
        c = Cipher(algorithms.AES(key), modes.OFB(_iv(idx, page))).decryptor()
        out += ph + c.update(bytes(page)) + c.finalize()
        i += PH + PAGE
    return bytes(out)


def carve_clientkey(wal):
    ps = struct.unpack(">i", wal[8:12])[0]; off = 32; last = None
    while off + 24 + ps <= len(wal):
        pstart = off + 24; pend = pstart + ps; c = pstart
        while c < pend - 15:
            rh = wal[c]
            if 5 <= rh <= 9:
                tAcc, tCK, tTs = wal[c + 1], wal[c + 2], wal[c + 4]
                if tCK >= 12 and tCK % 2 == 0 and 1 <= tTs <= 6 and (tAcc == 0 or tAcc <= 6):
                    blob = (tCK - 12) // 2
                    if 16 <= blob <= 64:
                        col1 = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}.get(tAcc, 0)
                        ds = c + rh + col1
                        if ds + blob <= pend:
                            last = wal[ds:ds + blob]; c += rh + col1 + blob - 1
            c += 1
        off += 24 + ps
    return last


def carve_nskeys(wal):
    ps = struct.unpack(">i", wal[8:12])[0]; off = 32; res = {}
    while off + 24 + ps <= len(wal):
        pstart = off + 24; pend = pstart + ps; c = pstart
        while c < pend - 10:
            if wal[c] == 3:
                tK, tV = wal[c + 1], wal[c + 2]
                if ((1 <= tK <= 6) or tK in (8, 9)) and (tV == 0 or (tV >= 12 and tV % 2 == 0)):
                    kl = {1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8}.get(tK, 0)
                    kv = 0 if tK == 8 else (1 if tK == 9 else None)
                    if kl and c + 3 + kl <= pend:
                        kv = int.from_bytes(wal[c + 3:c + 3 + kl], "big", signed=True)
                    if tV >= 12:
                        bs = (tV - 12) // 2; vs = c + 3 + kl
                        if vs + bs <= pend and bs > 0:
                            res[kv] = wal[vs:vs + bs]
                        c += 3 + kl + bs - 1
            c += 1
        off += 24 + ps
    return res


def pbkdf2(pw, salt, n):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=n, salt=salt, iterations=ITER).derive(pw)


def read_shared(path):
    import io
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        return os.read(fd, os.fstat(fd).st_size)
    finally:
        os.close(fd)


def find_localstate():
    base = os.path.join(os.environ["LOCALAPPDATA"], "Packages")
    for d in glob.glob(os.path.join(base, PKG_GLOB)):
        ls = os.path.join(d, "LocalState")
        if os.path.isdir(ls):
            return ls
    raise SystemExit("WhatsApp Desktop package not found under %LOCALAPPDATA%\\Packages")


def default_outdir():
    return os.path.join(os.environ["LOCALAPPDATA"], "Temp", "wa-decrypted")


def main():
    args = [a for a in sys.argv[1:] if a != "--purge"]
    outdir = args[0] if args else default_outdir()
    if "--purge" in sys.argv[1:]:
        n = wa_store.purge(outdir)
        print("purged {} ({} file(s))".format(outdir, n) if n else "nothing to purge at " + outdir)
        return
    gone = wa_store.purge(outdir)
    if gone:
        print("purged {} file(s) from a previous run before writing".format(gone))
    os.makedirs(outdir, exist_ok=True)
    ls = find_localstate()
    sess_dir = None
    for d in glob.glob(os.path.join(ls, "sessions", "*")):
        if os.path.isdir(d):
            sess_dir = d; break
    if not sess_dir:
        raise SystemExit("no session directory found (is WhatsApp linked?)")

    od = oduid()
    ssec = session_secret()

    # session.db-wal -> clientKey
    sess_wal = dec_wal(ssec, read_shared(os.path.join(ls, "session.db-wal")))
    client_key = carve_clientkey(sess_wal)
    if not client_key:
        raise SystemExit("clientKey not recovered from session.db-wal")

    # verify: sha1(clientKey) names the session dir
    want = hashlib.sha1(client_key).hexdigest().upper()
    if os.path.basename(sess_dir).upper() != want:
        print(f"WARN: session dir {os.path.basename(sess_dir)} != sha1(clientKey) {want}", file=sys.stderr)

    # nativeSettings key: PBKDF2 chain + AES-CBC(staticKey)
    aux = pbkdf2(client_key, od, 32)
    iv = pbkdf2(aux, od, 16)
    enc = Cipher(algorithms.AES(aux), modes.CBC(iv)).encryptor()
    pad = padding.PKCS7(128).padder()
    ns_key = (enc.update(pad.update(STATIC) + pad.finalize()) + enc.finalize())[:64]

    ns_wal = dec_wal(ns_key, read_shared(os.path.join(sess_dir, "nativeSettings.db-wal")))
    keys = carve_nskeys(ns_wal)
    if 1 not in keys:
        raise SystemExit("type-1 (messages) key not found in nativeSettings.db-wal")

    targets = {
        "genericStorage": keys[1],           # messages
        "contacts": keys.get(2),             # contacts / names
        "contactsState": keys.get(2),
    }
    for name, key in targets.items():
        if not key:
            continue
        for suffix, fn in ((".db", dec_db), ("-wal", dec_wal)):
            src = os.path.join(sess_dir, name + ".db" + ("" if suffix == ".db" else "-wal"))
            src = os.path.join(sess_dir, name + suffix if suffix == "-wal" else name + ".db")
            src = os.path.join(sess_dir, f"{name}.db{'' if suffix=='.db' else '-wal'}")
            if not os.path.exists(src):
                continue
            dec = fn(key, read_shared(src))
            out = os.path.join(outdir, f"{name}.dec.db{'' if suffix=='.db' else '-wal'}")
            with open(out, "wb") as f:
                f.write(dec)
            print(f"wrote {out} ({len(dec)} bytes)")
    wa_store.stamp(outdir)
    print(f"\nDone. Decrypted store in: {outdir}")
    print("This contains all your messages. It is local only; do not commit or share it.")
    print("It expires in {} minutes: wa_query refuses to read it after that and deletes it."
          .format(int(wa_store.DEFAULT_TTL_SECONDS // 60)))
    print("To remove it now: python wa_decrypt.py --purge")


if __name__ == "__main__":
    main()
