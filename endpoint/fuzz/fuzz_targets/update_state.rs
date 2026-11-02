#![no_main]
use k256::ecdsa::{signature::Signer, Signature, SigningKey};
use pge_update::{decide, public_key, sha256, Outcome, Refusal, State, Update};

fn hex(data: &[u8]) -> String {
    data.iter().map(|b| format!("{b:02x}")).collect()
}

fn sign(key: &SigningKey, message: &[u8]) -> Vec<u8> {
    let sig: Signature = key.sign(message);
    format!("{}\n", hex(&sig.to_bytes())).into_bytes()
}

fn decimal(x: u64) -> u64 {
    1 + x % 9_999_999_999_999_999_999
}

// A correctly signed update with fuzzer-chosen versions, against any stored state the fuzzer writes:
// the device only ever moves forward, and one version always means one manifest and one key list.
libfuzzer_sys::fuzz_target!(|raw: &[u8]| {
    if raw.len() < 17 {
        return;
    }
    let version = decimal(u64::from_le_bytes(raw[..8].try_into().unwrap()));
    let keys_version = decimal(u64::from_le_bytes(raw[8..16].try_into().unwrap()));
    let spin = raw[16] % 4;
    let Ok(stored) = State::parse(&raw[17..]) else {
        return;
    };
    let root = SigningKey::from_slice(&[1; 32]).unwrap();
    let ops = SigningKey::from_slice(&[2; 32]).unwrap();
    let pub_hex = |k: &SigningKey| hex(&k.verifying_key().to_encoded_point(true).to_bytes());
    let files: [&[u8]; 4] = [b"settings", b"vk", b"srs", b"domain"];
    let keys = format!("pge-keys 1\nversion {keys_version}\nkey ops-1 {}\n", pub_hex(&ops));
    let mut manifest = format!("pge-update 1\ndevice pi-1\nversion {version}\n");
    for (name, data) in pge_update::FILES.iter().zip(files) {
        manifest += &format!("{name} {}\n", sha256(data));
    }
    manifest += &format!("release fixed\ndeadline-ms 4000\nspin-ms {spin}\nproof-bytes 3072\nmax-pending 32\nhalt none\ncap none\nkey ops-1\n");
    let update = Update {
        keys: keys.as_bytes(),
        keys_signature: &sign(&root, keys.as_bytes()),
        manifest: manifest.as_bytes(),
        manifest_signature: &sign(&ops, manifest.as_bytes()),
        files,
    };
    let root_pub = public_key(&pub_hex(&root)).unwrap();
    let keys_digest = sha256(keys.as_bytes());
    let digest = sha256(manifest.as_bytes());
    match decide(&root_pub, "pi-1", Some(&stored), &update) {
        Ok(Outcome::Apply(new)) => {
            assert!(new.version >= stored.version && new.keys >= stored.keys);
            assert!(new.version > stored.version || new.digest == stored.digest);
            assert!(new.keys > stored.keys || new.keys_digest == stored.keys_digest);
            assert!(new.version > stored.version || new.keys > stored.keys);
            assert_eq!(new, State { version, keys: keys_version, keys_digest, digest });
        }
        Ok(Outcome::Same) => {
            assert_eq!(stored, State { version, keys: keys_version, keys_digest, digest });
        }
        Err(Refusal::Rollback) => assert!(version < stored.version || keys_version < stored.keys),
        Err(Refusal::Replay) => assert!(
            (keys_version == stored.keys && keys_digest != stored.keys_digest)
                || (version == stored.version && digest != stored.digest)
        ),
        Err(other) => panic!("a valid update was refused: {other:?}"),
    }
    // With no stored state the same update is always applied.
    assert!(matches!(decide(&root_pub, "pi-1", None, &update), Ok(Outcome::Apply(_))));
});
