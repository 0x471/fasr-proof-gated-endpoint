"""Seed inputs for the update fuzz targets: valid manifests, key lists and states, and stored states that
hit each outcome of update_state (same, forward, key rotation, replay, rollback). Usage: python3 seeds.py CORPUS_DIR
The ops key is the scalar 0x0202...02 used in fuzz_targets/update_state.rs; secp256k1 is computed here directly."""
import hashlib, struct, os, sys
P=2**256-2**32-977; N=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G=(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
def add(a,b):
    if a is None: return b
    if b is None: return a
    if a[0]==b[0] and (a[1]+b[1])%P==0: return None
    l=((3*a[0]*a[0])*pow(2*a[1],-1,P) if a==b else (b[1]-a[1])*pow(b[0]-a[0],-1,P))%P
    x=(l*l-a[0]-b[0])%P; return (x,(l*(a[0]-x)-a[1])%P)
def mul(k):
    r=None; q=G
    while k:
        if k&1: r=add(r,q)
        q=add(q,q); k>>=1
    return r
def comp(pt): return ('02' if pt[1]%2==0 else '03')+format(pt[0],'064x')
assert comp(mul(1))=='0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'
ops=comp(mul(int.from_bytes(bytes([2]*32),'big')))
sha=lambda b: hashlib.sha256(b).hexdigest()
def texts(v,k,spin):
    keys=f"pge-keys 1\nversion {k}\nkey ops-1 {ops}\n".encode()
    m=f"pge-update 1\ndevice pi-1\nversion {v}\n"
    for n,d in zip(["settings.json","vk.key","kzg.srs","domain.json"],[b"settings",b"vk",b"srs",b"domain"]): m+=f"{n} {sha(d)}\n"
    m+=f"release fixed\ndeadline-ms 4000\nspin-ms {spin}\nproof-bytes 3072\nmax-pending 32\nhalt none\ncap none\nkey ops-1\n"
    return keys,m.encode()
def state(v,k,kd,d): return f"pge-state 1\nversion {v}\nkeys {k}\nkeys-digest {kd}\ndigest {d}\n".encode()
out=sys.argv[1]
os.makedirs(f"{out}/update_state",exist_ok=True); os.makedirs(f"{out}/update_text",exist_ok=True)
hdr=lambda v,k,spin: struct.pack('<QQB',v-1,k-1,spin)
keys,m=texts(1,1,0)
same=state(1,1,sha(keys),sha(m))
seeds={"same":hdr(1,1,0)+same,"forward":hdr(2,1,0)+same,"rotate":hdr(1,2,0)+same,"replay":hdr(1,1,1)+same,
       "rollback":hdr(1,1,0)+state(2,1,sha(keys),sha(m)),"keyreplay":hdr(2,1,0)+state(1,1,'0'*64,sha(m))}
for n,b in seeds.items(): open(f"{out}/update_state/{n}",'wb').write(b)
for n,b in {"manifest":m,"keys":keys,"state":same,"manifest_cap":m.replace(b"cap none",b"cap 64 1 64").replace(b"halt none",b"halt 3")}.items(): open(f"{out}/update_text/{n}",'wb').write(b)
print("ok", ops)
