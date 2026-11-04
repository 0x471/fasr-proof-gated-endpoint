import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "observer"))

from pge.protocol import Wire, frame  # noqa: E402
from pcap_trace import analyse  # noqa: E402
from jitter_test import load_ms  # noqa: E402

WIRE = Wire((4,), (3,))
X = [[0.5, -0.2, 0.9, 0.1]]
LAPTOP, PI = bytes([192, 168, 2, 1]), bytes([192, 168, 2, 2])


def packet(t, outbound, seq, payload, flags=0x18, ttl=64, window=500, client_port=50000):
    src, dst = (PI, LAPTOP) if outbound else (LAPTOP, PI)
    sport, dport = (8700, client_port) if outbound else (client_port, 8700)
    tcp = struct.pack(">HHIIBBHHH", sport, dport, seq, 0, 5 << 4, flags, window, 0, 0) + payload
    ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp), 1, 0x4000, ttl, 6, 0, src, dst) + tcp
    eth = b"\x00" * 12 + b"\x08\x00" + ip + b"\x00" * 6
    sec, usec = int(t), round((t - int(t)) * 1e6)
    return struct.pack("<IIII", sec, usec, len(eth), len(eth)) + eth


def capture(pkts):
    return struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1) + b"".join(pkts)


def test_times_come_from_the_packet_holding_each_frames_last_byte():
    r0, r1 = frame(WIRE.encode_request(0, X)), frame(WIRE.encode_request(1, X))
    a0, a1 = frame(WIRE.reply_ok(0, [[1.0, 2.0, 3.0]])), frame(WIRE.reply_error(1, "unavailable"))
    pkts = [packet(10.0, False, 1000, r0), packet(10.0005, True, 7000, a0[:10]), packet(14.0012, True, 7010, a0[10:]),
            packet(11.0, False, 1000 + len(r0), r1), packet(15.0, True, 7000 + len(a0), a1),
            packet(15.2, True, 7000 + len(a0), a1)]
    summary, trace = analyse(capture(pkts))
    assert [r["id"] for r in trace] == [0, 1] and [r["answer"]["ok"] for r in trace] == [True, False]
    assert [r["elapsed_ms"] for r in trace] == [4001.2, 4000.0]
    assert summary["replies"] == 2 and summary["connections"] == 1
    assert summary["reply_payload_bytes"] == {10: 1, len(a0) - 10: 1, len(a1): 1}
    assert summary["frames_completed_per_payload_packet"] == {0: 1, 1: 2}


def test_trace_reads_like_an_observer_trace(tmp_path):
    pkts, seq_in, seq_out = [], 1, 1
    for i in range(4):
        r, a = frame(WIRE.encode_request(i, X)), frame(WIRE.reply_ok(i, [[0.0, 0.0, 0.0]]))
        pkts += [packet(i, False, seq_in, r), packet(i + 4.001, True, seq_out, a)]
        seq_in, seq_out = seq_in + len(r), seq_out + len(a)
    _, trace = analyse(capture(pkts))
    path = tmp_path / "t.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in trace))
    assert load_ms(str(path), "0101") == [4001.0] * 4


def test_a_missing_segment_is_refused():
    r0 = frame(WIRE.encode_request(0, X))
    with pytest.raises(ValueError):
        analyse(capture([packet(1.0, False, 1000, r0[:5]), packet(1.1, False, 1010, r0[10:])]))


def test_a_reply_for_an_id_never_requested_is_refused():
    r0, a5 = frame(WIRE.encode_request(0, X)), frame(WIRE.reply_ok(5, [[0.0, 0.0, 0.0]]))
    with pytest.raises(ValueError):
        analyse(capture([packet(1.0, False, 1, r0), packet(5.0, True, 1, a5)]))


def test_a_capture_started_mid_connection_needs_partial():
    r1 = frame(WIRE.encode_request(1, X))
    a0, a1 = frame(WIRE.reply_ok(0, [[1.0, 2.0, 3.0]])), frame(WIRE.reply_ok(1, [[1.0, 2.0, 3.0]]))
    # The request for id 0 was sent before the capture started; only its reply is in it.
    pkts = [packet(14.0, True, 7000, a0), packet(15.0, False, 2000, r1), packet(19.0, True, 7000 + len(a0), a1)]
    with pytest.raises(ValueError):
        analyse(capture(pkts))
    summary, trace = analyse(capture(pkts), partial=True)
    assert summary["replies_to_uncaptured_requests"] == 1 and summary["replies"] == 1
    assert [r["elapsed_ms"] for r in trace] == [4000.0]
