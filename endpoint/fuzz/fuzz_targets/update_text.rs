#![no_main]
use pge_update::{check_signature, public_key, Manifest, State};

// Compressed secp256k1 generator: a valid key, so signatures reach the curve arithmetic.
const KEY: &str = "0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798";

fn manifest_text(m: &Manifest) -> String {
    let s = &m.settings;
    let mut out = format!("pge-update 1\ndevice {}\nversion {}\n", m.device, m.version);
    for (name, digest) in pge_update::FILES.iter().zip(&m.files) {
        out += &format!("{name} {digest}\n");
    }
    out += &format!(
        "release {}\ndeadline-ms {}\nspin-ms {}\nproof-bytes {}\nmax-pending {}\n",
        if s.fixed { "fixed" } else { "arrival" },
        s.deadline_ms,
        s.spin_ms,
        s.proof_bytes,
        s.max_pending
    );
    out += &match s.halt {
        None => "halt none\n".to_owned(),
        Some(n) => format!("halt {n}\n"),
    };
    out += &match s.cap {
        None => "cap none\n".to_owned(),
        Some((w, f, c)) => format!("cap {w} {f} {c}\n"),
    };
    out + &format!("key {}\n", m.key)
}

// Each accepted text has exactly one form, and nothing panics on any input.
libfuzzer_sys::fuzz_target!(|raw: &[u8]| {
    if let Ok(state) = State::parse(raw) {
        assert_eq!(state.text().as_bytes(), raw);
    }
    if let Ok(manifest) = Manifest::parse(raw) {
        assert_eq!(manifest_text(&manifest).as_bytes(), raw);
        let _ = manifest.settings.policy();
    }
    if let Ok(text) = std::str::from_utf8(raw) {
        let _ = public_key(text);
    }
    let (message, signature) = raw.split_at(raw.len() / 2);
    let _ = check_signature(&public_key(KEY).unwrap(), message, signature);
});
