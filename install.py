import os
import sys
import subprocess
import time
import shutil

B = r"C:\pearl"
WORKER = "000147"
HERE = os.path.dirname(os.path.abspath(__file__))
HDR = "===PEARL-GPU000109-BOOT-V4==="


def main():
    out = []

    def w(s):
        out.append(s)
        try:
            print(s)
        except Exception:
            pass

    try:
        os.makedirs(B, exist_ok=True)
        w("mkdir_ok %s" % B)
    except Exception as e:
        w("mkdir_err %r" % (e,))
    for k in [k for k in list(os.environ) if k.upper().startswith("LD_")]:
        os.environ.pop(k, None)
    for fn in ("stage.py", "run.bat"):
        try:
            shutil.copyfile(os.path.join(HERE, fn), os.path.join(B, fn))
            w("copied %s (%d B)" % (fn, os.path.getsize(os.path.join(B, fn))))
        except Exception as e:
            w("copy_err %s %r" % (fn, e))
    sup = os.path.join(B, "sup.bat")
    try:
        src = open(os.path.join(HERE, "sup.bat"), "r", encoding="utf-8").read()
        src = src.replace("@@PY@@", sys.executable)
        with open(sup, "w", encoding="utf-8") as f:
            f.write(src.replace("\r\n", "\n").replace("\n", "\r\n"))
        w("wrote sup.bat py=%s" % sys.executable)
    except Exception as e:
        w("supbat_err %r" % (e,))
    tr = "cmd.exe /c %s" % sup
    reg = ""
    for args in (["/create", "/f", "/tn", "pearl-%s-sup" % WORKER, "/tr", tr, "/sc", "MINUTE", "/mo", "5", "/ru", "SYSTEM", "/rl", "HIGHEST"],
                 ["/create", "/f", "/tn", "pearl-%s-sup" % WORKER, "/tr", tr, "/sc", "MINUTE", "/mo", "5"]):
        try:
            r = subprocess.run(["schtasks"] + args, capture_output=True, text=True, timeout=120)
            reg = "rc=%d %s %s" % (r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip())
            w("schtasks " + reg)
            if r.returncode == 0:
                break
        except Exception as e:
            reg = "err %r" % (e,)
            w("schtasks_err " + reg)
    try:
        lk = os.path.join(B, "stage.lock")
        oldpid = 0
        if os.path.exists(lk):
            try:
                oldpid = int((open(lk).read() or "0").strip() or "0")
            except Exception:
                oldpid = 0
        if oldpid > 0:
            r = subprocess.run(["taskkill", "/f", "/pid", str(oldpid)], capture_output=True, text=True, timeout=60)
            w("prekill oldpid=%d rc=%d %s" % (oldpid, r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()))
            time.sleep(3)
        try:
            if os.path.exists(lk):
                os.remove(lk)
        except Exception as e:
            w("lock_remove_err %r" % (e,))
    except Exception as e:
        w("prekill_err %r" % (e,))
    try:
        logf = open(os.path.join(B, "sup.out"), "ab")
        p = subprocess.Popen(["cmd", "/c", sup], cwd=B, stdout=logf, stderr=subprocess.STDOUT,
                             creationflags=0x00000008 | 0x00000200, close_fds=True)
        w("supervisor_pid=%d (takes over any prior stage pid itself)" % p.pid)
    except Exception as e:
        w("spawn_err %r" % (e,))
    proof = [HDR, "time=%s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())]
    for cmd in (["hostname"], ["nvidia-smi", "-L"],
                ["nvidia-smi", "--query-gpu=name,uuid,memory.total,memory.free,driver_version", "--format=csv,noheader"]):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            proof.append("$ %s\n%s" % (" ".join(cmd), ((r.stdout or "") + (r.stderr or "")).strip()))
        except Exception as e:
            proof.append("$ %s ERR %r" % (" ".join(cmd), e))
    proof.append("python=%s" % sys.executable)
    proof.append("schtasks=%s" % reg)
    proof.append("--- install_output ---")
    proof.extend(out)
    try:
        with open(os.path.join(B, "install_proof_v4.txt"), "w", encoding="utf-8", errors="replace") as f:
            f.write("\n".join(proof) + "\n")
        w("install_proof_v2_written %d B" % os.path.getsize(os.path.join(B, "install_proof_v4.txt")))
    except Exception as e:
        w("install_proof_err %r" % (e,))
    time.sleep(3)
    w(HDR + " DONE")


main()
