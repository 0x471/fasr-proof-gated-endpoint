"""TCP connect scan of every port: which are open, refused (the host answered) or dropped (no answer).

Usage: /usr/bin/python3 device/tcp_scan.py HOST [--ports 1-65535] [--timeout 1.0] [--concurrency 256]
Prints one JSON line: counts per outcome and the open and refused ports (refused ports listed only if
fewer than 100). A firewall that drops shows every closed port as "dropped". On macOS run it with
/usr/bin/python3: a Homebrew Python may lack Local Network access, which looks like timeouts.
"""
from __future__ import annotations

import argparse
import asyncio
import json


async def probe(host: str, port: int, timeout: float, gate: asyncio.Semaphore) -> tuple[int, str]:
    async with gate:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        except asyncio.TimeoutError:
            return port, "dropped"
        except ConnectionRefusedError:
            return port, "refused"
        except OSError:
            return port, "error"
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        return port, "open"


async def scan(host: str, lo: int, hi: int, timeout: float, concurrency: int) -> dict:
    gate = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*(probe(host, p, timeout, gate) for p in range(lo, hi + 1)))
    by = {k: sorted(p for p, r in results if r == k) for k in ("open", "refused", "dropped", "error")}
    return {"host": host, "ports": f"{lo}-{hi}", "timeout_s": timeout,
            **{f"n_{k}": len(v) for k, v in by.items()},
            "open": by["open"], "refused": by["refused"] if len(by["refused"]) < 100 else "many",
            "error": by["error"][:20]}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host")
    ap.add_argument("--ports", default="1-65535")
    ap.add_argument("--timeout", type=float, default=1.0)
    ap.add_argument("--concurrency", type=int, default=256)
    a = ap.parse_args(argv)
    lo, hi = (int(x) for x in a.ports.split("-"))
    if not 1 <= lo <= hi <= 65535:
        raise SystemExit("ports must be a range within 1-65535")
    print(json.dumps(asyncio.run(scan(a.host, lo, hi, a.timeout, a.concurrency))))


if __name__ == "__main__":
    main()
