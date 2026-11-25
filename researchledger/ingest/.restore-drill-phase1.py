import hashlib, json, os, secrets, shutil, sys, time, gzip

SRC = r"G:\corpus-offload-20261029T050708Z-67591dab\corpus-backup.sqlite.gz"
DEST_ROOT = "G:\\"
EXPECT_SHA = "d490e956d2acdf3437959d9f3bf6abf09f6655179891b6f0f32dfe3eb02dcb54"
EXPECT_BYTES = 4714205734
EXPECT_DECOMP = 16371769344
GIB = 1024 ** 3
MIN_FREE = 50 * GIB

rec = {"phase": 1, "host": "desk-native-windows", "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

def out(k, v):
    rec[k] = v
    print("%s=%s" % (k, v), flush=True)

def done(code, note=""):
    rec["note"] = note
    rec["exit"] = code
    rec["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print("RECEIPT_JSON=" + json.dumps(rec, sort_keys=True), flush=True)
    sys.exit(code)

t0 = time.time()
u = shutil.disk_usage(DEST_ROOT)
out("g_free_bytes", u.free)
out("g_free_gib", round(u.free / GIB, 2))
out("g_total_bytes", u.total)
if u.free < MIN_FREE:
    done(9, "BLOCKED: G free below 50 GiB; no writes performed")

if not os.path.isfile(SRC):
    done(3, "source archive missing")
out("src_bytes", os.path.getsize(SRC))

h = hashlib.sha256()
with open(SRC, "rb") as f:
    for b in iter(lambda: f.read(8 << 20), b""):
        h.update(b)
out("src_sha256", h.hexdigest())
if h.hexdigest() != EXPECT_SHA:
    done(4, "SHA mismatch on source archive; refusing to restore")

# exclusive, unpredictable directory
name = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-restore-" + secrets.token_hex(8)
dest_dir = os.path.join(DEST_ROOT, name)
os.mkdir(dest_dir)  # raises if exists -> exclusivity by construction
if os.listdir(dest_dir):
    done(5, "new dir not empty")
out("dest_dir", dest_dir)

dest = os.path.join(dest_dir, "corpus-restored.sqlite")
t1 = time.time()
written = 0
try:
    with gzip.open(SRC, "rb") as g, open(dest, "xb") as o:
        for chunk in iter(lambda: g.read(16 << 20), b""):
            o.write(chunk)
            written += len(chunk)
        o.flush()
        os.fsync(o.fileno())
except (EOFError, gzip.BadGzipFile, OSError) as e:
    done(6, "decompress failure (%s): %s" % (type(e).__name__, e))
out("decompressed_bytes", written)
out("decompress_seconds", round(time.time() - t1, 2))
out("crc_eof_ok", True)
if written != EXPECT_DECOMP:
    done(7, "decompressed size mismatch")
if os.path.getsize(dest) != EXPECT_DECOMP:
    done(7, "on-disk size mismatch after fsync")
out("dest_path", dest)
out("dest_bytes_ondisk", os.path.getsize(dest))
out("phase1_total_seconds", round(time.time() - t0, 2))
done(0, "phase1 ok: archive verified, decompressed, fsync, size+CRC checked")
