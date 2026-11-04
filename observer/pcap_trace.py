"""Answer times and packet details from a capture of the outside link (tcpdump -w, port 8700).

Usage: python3 observer/pcap_trace.py CAPTURE.pcap [--port 8700] [--trace OUT.jsonl] > summary.json
Reassembles each TCP connection in both directions, cuts it into endpoint frames (4-byte length, then
the message) and pairs each request with the reply carrying the same id on that connection. A frame's
time is the capture time of the packet holding its last byte, so elapsed_ms here leaves out the
observer program's own scheduling. --trace writes one row per reply, numbered in the order the requests
were sent ({"id", "elapsed_ms", "answer": {"id", "ok"}}), which observer/jitter_test.py reads like an
observer trace. The summary lists what the endpoint's packets looked like: payload sizes, packets per
reply, TCP flags, TTL and window values, so a run where the server misbehaves can be compared with an
honest one. IPv4 only; Ethernet, BSD loopback or raw IP captures.
"""
from __future__ import annotations

import argparse
import collections
import json
import struct
import sys

LINKS = {1: "ethernet", 0: "null", 101: "raw", 12: "raw", 108: "null"}


def packets(data: bytes):
    """Yield (time in seconds, IPv4 packet bytes) from a classic pcap file."""
    magic = data[:4]
    order = {b"\xd4\xc3\xb2\xa1": "<", b"\xa1\xb2\xc3\xd4": ">", b"\x4d\x3c\xb2\xa1": "<", b"\xa1\xb2\x3c\x4d": ">"}
    if magic not in order:
        raise ValueError("not a classic pcap file (pcapng isn't supported; use tcpdump -w)")
    e = order[magic]
    scale = 1e-9 if magic in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d") else 1e-6
    link = struct.unpack(e + "I", data[20:24])[0]
    if link not in LINKS:
        raise ValueError(f"link type {link} isn't supported")
    pos = 24
    while pos + 16 <= len(data):
        sec, frac, incl, _ = struct.unpack(e + "IIII", data[pos:pos + 16])
        frame = data[pos + 16:pos + 16 + incl]
        pos += 16 + incl
        if LINKS[link] == "ethernet":
            kind, off = struct.unpack(">H", frame[12:14])[0], 14
            while kind == 0x8100:
                kind, off = struct.unpack(">H", frame[off + 2:off + 4])[0], off + 4
            if kind != 0x0800:
                continue
            ip = frame[off:]
        elif LINKS[link] == "null":
            ip = frame[4:]
        else:
            ip = frame
        if len(ip) >= 20 and ip[0] >> 4 == 4:
            yield sec + frac * scale, ip


def segments(data: bytes, port: int):
    """Yield TCP segments to or from port: (time, (client address, client port), to_endpoint, seq, flags,
    ttl, window, payload)."""
    for t, ip in packets(data):
        ihl = (ip[0] & 15) * 4
        total = struct.unpack(">H", ip[2:4])[0]
        if ip[9] != 6 or ip[6] & 0x3F or ip[7]:
            continue
        tcp = ip[ihl:total]
        sport, dport, seq = struct.unpack(">HHI", tcp[:8])
        doff = (tcp[12] >> 4) * 4
        flags, window = tcp[13], struct.unpack(">H", tcp[14:16])[0]
        src, dst = ".".join(map(str, ip[12:16])), ".".join(map(str, ip[16:20]))
        if dport == port:
            yield t, (src, sport), True, seq, flags, ip[8], window, tcp[doff:]
        elif sport == port:
            yield t, (dst, dport), False, seq, flags, ip[8], window, tcp[doff:]


class Stream:
    """One direction of one connection: in-order bytes, and the time each byte arrived."""

    def __init__(self):
        self.next, self.buf, self.times, self.frames = None, b"", [], []

    def add(self, t: float, seq: int, payload: bytes) -> int:
        if self.next is None:
            self.next = seq
        skip = (self.next - seq) % (1 << 32)
        if skip >= 1 << 31:
            raise ValueError("a gap in the capture: a segment is missing")
        new = payload[skip:] if skip < len(payload) else b""
        self.next = (self.next + len(new)) % (1 << 32)
        self.buf += new
        self.times += [t] * len(new)
        while len(self.buf) >= 4:
            n = struct.unpack(">I", self.buf[:4])[0]
            if len(self.buf) < 4 + n:
                break
            self.frames.append((self.times[3 + n], self.buf[4:4 + n]))
            self.buf, self.times = self.buf[4 + n:], self.times[4 + n:]
        return len(new)


def analyse(data: bytes, port: int = 8700, partial: bool = False) -> tuple[dict, list[dict]]:
    """partial: the capture started after a connection did; replies to requests it didn't see are
    skipped and counted instead of refused. Reassembly then starts at the first packet seen, so this
    only reads correctly when packets carry whole frames (frames_completed_per_payload_packet)."""
    streams = collections.defaultdict(Stream)
    per_reply_packets = collections.Counter()
    out_sizes, flags_seen, ttls, windows = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    for t, conn, inbound, seq, flags, ttl, window, payload in segments(data, port):
        if inbound:
            if payload:
                streams[(conn, True)].add(t, seq, payload)
            continue
        flags_seen[flags] += 1
        ttls[ttl] += 1
        windows[window] += 1
        if payload:
            s = streams[(conn, False)]
            before = len(s.frames)
            if s.add(t, seq, payload):
                out_sizes[len(payload)] += 1
                per_reply_packets[len(s.frames) - before] += 1
    rows, unmatched = [], 0
    for (conn, inbound), s in list(streams.items()):
        if not inbound:
            continue
        sent = {}
        for t, body in s.frames:
            if body[:1] != b"\x01" or len(body) < 9:
                raise ValueError("a client frame that isn't a request")
            sent.setdefault(struct.unpack(">Q", body[1:9])[0], t)
        for t, body in streams[(conn, False)].frames:
            if body[:1] != b"\x04" or len(body) < 10:
                raise ValueError("an endpoint frame that isn't a reply")
            rid = struct.unpack(">Q", body[1:9])[0]
            if rid not in sent:
                if partial:
                    unmatched += 1
                    continue
                raise ValueError(f"a reply for id {rid}, which wasn't requested on that connection")
            rows.append({"sent": sent[rid], "conn": conn, "rid": rid, "elapsed_ms": round((t - sent[rid]) * 1000, 3),
                         "ok": body[9] == 0})
    rows.sort(key=lambda r: r["sent"])
    trace = [{"id": i, "elapsed_ms": r["elapsed_ms"], "answer": {"id": i, "ok": r["ok"]}} for i, r in enumerate(rows)]
    summary = {"connections": len({c for c, _ in streams}), "replies": len(rows),
               "reply_payload_bytes": dict(sorted(out_sizes.items())),
               "frames_completed_per_payload_packet": dict(sorted(per_reply_packets.items())),
               "tcp_flags_from_endpoint": {f"0x{k:02x}": v for k, v in sorted(flags_seen.items())},
               "ttl_from_endpoint": dict(sorted(ttls.items())), "distinct_windows_from_endpoint": len(windows)}
    if partial:
        summary["replies_to_uncaptured_requests"] = unmatched
    return summary, trace


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture")
    ap.add_argument("--port", type=int, default=8700)
    ap.add_argument("--trace")
    ap.add_argument("--partial", action="store_true", help="the capture started mid-connection")
    a = ap.parse_args(argv)
    summary, trace = analyse(open(a.capture, "rb").read(), a.port, a.partial)
    if a.trace:
        with open(a.trace, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in trace)
    json.dump(summary, sys.stdout)
    print()


if __name__ == "__main__":
    main()
