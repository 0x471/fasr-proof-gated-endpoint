"""Does the endpoint notice a silently dead server connection and redial? A manual check: Linux, root.

Usage from the repo root: sudo -E env PGE_SRS=/abs/kzg.srs python3 device/halfopen_check.py ENDPOINT_BINARY
1. The endpoint connects to a test server process on a fixed loopback port.
2. iptables drops that port both ways, so no FIN, RST or data reaches either side.
3. The server process is killed: its FIN is dropped, so the endpoint's connection is left half open.
4. After DEAD_S seconds the rules go, a new server starts on the same port, and we wait up to WAIT_S
   seconds for the endpoint to connect again, with no client question in between.
Prints what happened; exit 0 if it reconnected.
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path.cwd()
BIN = sys.argv[1]
DEAD_S = float(os.environ.get("DEAD_S", "150"))
WAIT_S = float(os.environ.get("WAIT_S", "60"))
PY = os.environ.get("PY", sys.executable)
SRS = os.environ["PGE_SRS"]
TINY = ROOT / "tests/fixtures/tiny"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def rules(op, port, check=True):
    for chain, iface in (("INPUT", "-i"), ("OUTPUT", "-o")):
        for flag in ("--dport", "--sport"):
            subprocess.run(["iptables", op, chain, "-p", "tcp", iface, "lo", flag, str(port), "-j", "DROP"],
                           check=check, stderr=None if check else subprocess.DEVNULL)


def established(port):
    out = subprocess.run(["ss", "-Htn", "state", "established", f"( sport = :{port} )"],
                         capture_output=True, text=True).stdout
    return sum(1 for line in out.splitlines() if line.strip())


def server(port, log):
    # A bare listener that accepts and holds connections: enough, since no question is asked.
    code = ("import socket,sys\ns=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\n"
            f"s.bind(('127.0.0.1',{port}));s.listen(8);print('listening',file=sys.stderr,flush=True)\nc=[]\n"
            "while True:\n c.append(s.accept()[0])")
    p = subprocess.Popen([PY, "-c", code], stderr=open(log, "w"), stdout=subprocess.DEVNULL)
    for _ in range(200):
        if "listening" in Path(log).read_text():
            return p
        time.sleep(0.1)
    raise SystemExit("server did not start")


def wait_for(cond, limit):
    t = time.monotonic()
    while time.monotonic() - t < limit:
        if cond():
            return time.monotonic() - t
        time.sleep(0.2)
    return None


work = Path(tempfile.mkdtemp())
for name in ("settings.json", "vk.key"):
    shutil.copy(TINY / name, work / name)
shutil.copy(SRS, work / "kzg.srs")
sport, lport = free_port(), free_port()
srv = server(sport, work / "server1.log")
ep = subprocess.Popen([BIN, "--listen", f"127.0.0.1:{lport}", "--server", f"127.0.0.1:{sport}", "--bundle", str(work),
                       "--pins", str(ROOT / "device/tiny.sha256"), "--domain", str(TINY / "domain.json"),
                       "--proof-bytes", "3072", "--log", str(work / "endpoint.log")], stderr=subprocess.DEVNULL)
try:
    t = wait_for(lambda: established(sport) > 0, 20)
    print(f"endpoint connected to the server: {t is not None}")
    rules("-A", sport)
    srv.kill()
    srv.wait()
    print(f"link dropped silently and the server killed; waiting {DEAD_S:.0f} s")
    time.sleep(DEAD_S)
    rules("-D", sport)
    srv = server(sport, work / "server2.log")
    t = wait_for(lambda: established(sport) > 0, WAIT_S)
    print("rules removed, new server up; endpoint reconnected: " + (f"yes, after {t:.1f} s" if t is not None else f"no (not within {WAIT_S:.0f} s)"))
    print("endpoint log words:", sorted({l.split('"result":"')[1].split('"')[0] for l in open(work / "endpoint.log") if '"result":"' in l}))
    sys.exit(0 if t is not None else 1)
finally:
    rules("-D", sport, check=False)
    ep.kill()
    srv.kill()
