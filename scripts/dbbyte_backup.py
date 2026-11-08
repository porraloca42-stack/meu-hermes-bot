#!/usr/bin/python3
"""Authenticated encrypted Hermes backups on DBByte S3-compatible storage."""
import argparse, hashlib, json, os, subprocess, sys, tempfile, time, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
import boto3
from botocore.config import Config
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC=b"HERMES-DBBYTE-AESGCM1\n"; SALT_LEN=16; NONCE_LEN=12; TAG_LEN=16
CHUNK=1024*1024; PART_SIZE=90*1024*1024; PREFIX="backups/"

def log(msg): print("[dbbyte-backup] "+str(msg), flush=True)
def required(name):
    v=os.environ.get(name)
    if not v: raise RuntimeError("missing environment variable: "+name)
    return v
def bucket(): return os.environ.get("HERMES_BACKUP_BUCKET","hermes-backups")
def client():
    return boto3.client("s3",endpoint_url=os.environ.get("DBBYTE_ENDPOINT","https://s3.dbbyte.com"),
        region_name=os.environ.get("DBBYTE_REGION","auto"),
        aws_access_key_id=required("DBBYTE_ACCESS_KEY_ID"),
        aws_secret_access_key=required("DBBYTE_SECRET_ACCESS_KEY"),
        config=Config(s3={"addressing_style":"path"}))
def key_for(salt):
    password=required("HERMES_BACKUP_ENCRYPTION_PASSPHRASE").encode()
    if len(password)<32: raise RuntimeError("encryption passphrase must be at least 32 bytes")
    return PBKDF2HMAC(algorithm=hashes.SHA256(),length=32,salt=salt,iterations=600000).derive(password)
def encrypt(src,dst):
    salt=os.urandom(SALT_LEN); nonce=os.urandom(NONCE_LEN); header=MAGIC+salt+nonce
    enc=Cipher(algorithms.AES(key_for(salt)),modes.GCM(nonce)).encryptor()
    enc.authenticate_additional_data(header)
    with open(src,"rb") as r,open(dst,"wb") as w:
        w.write(header)
        for block in iter(lambda:r.read(CHUNK),b""): w.write(enc.update(block))
        w.write(enc.finalize()); w.write(enc.tag)
def decrypt(src,dst):
    size=os.path.getsize(src); hlen=len(MAGIC)+SALT_LEN+NONCE_LEN
    if size<hlen+TAG_LEN: raise RuntimeError("encrypted backup truncated")
    with open(src,"rb") as r:
        header=r.read(hlen)
        if not header.startswith(MAGIC): raise RuntimeError("unknown encrypted backup format")
        salt=header[len(MAGIC):len(MAGIC)+SALT_LEN]
        nonce=header[len(MAGIC)+SALT_LEN:]
        r.seek(-TAG_LEN,2); tag=r.read(TAG_LEN); r.seek(hlen)
        remaining=size-hlen-TAG_LEN
        dec=Cipher(algorithms.AES(key_for(salt)),modes.GCM(nonce,tag)).decryptor()
        dec.authenticate_additional_data(header)
        try:
            with open(dst,"wb") as w:
                while remaining:
                    b=r.read(min(CHUNK,remaining))
                    if not b: raise RuntimeError("encrypted backup ended unexpectedly")
                    remaining-=len(b); w.write(dec.update(b))
                w.write(dec.finalize())
        except Exception:
            try: os.unlink(dst)
            except OSError: pass
            raise RuntimeError("backup authentication failed (wrong passphrase or damaged file)")
def sha_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(CHUNK),b""): h.update(b)
    return h.hexdigest()
def manifests(s3):
    out=[]
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket(),Prefix=PREFIX):
        for obj in page.get("Contents",[]):
            if obj["Key"].endswith("/manifest.json"): out.append((obj["LastModified"],obj["Key"]))
    return sorted(out,reverse=True)
def check_zip(p):
    with zipfile.ZipFile(p) as z:
        bad=z.testzip()
        if bad: raise RuntimeError("ZIP CRC check failed: "+bad)
def backup_once():
    s3=client(); home=Path(os.environ.get("HERMES_HOME","/app/.cache/hermes-home"))
    keep=max(1,int(os.environ.get("HERMES_BACKUP_RETENTION","7")))
    bid=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
    prefix=PREFIX+bid+"/"
    with tempfile.TemporaryDirectory(prefix="hermes-backup-") as td:
        z=Path(td)/"hermes.zip"; enc=Path(td)/"hermes.aesgcm"
        p=subprocess.run(["hermes","backup","-o",str(z)],cwd=home,env={**os.environ,"HOME":str(home)})
        if p.returncode or not z.exists(): raise RuntimeError("hermes backup failed; refusing upload")
        check_zip(z); encrypt(z,enc); total=enc.stat().st_size; digest=sha_file(enc); parts=[]
        with open(enc,"rb") as src:
            i=0
            while True:
                block=src.read(PART_SIZE)
                if not block: break
                i+=1; k=f"{prefix}part-{i:04d}.bin"; ph=hashlib.sha256(block).hexdigest()
                s3.put_object(Bucket=bucket(),Key=k,Body=block,ContentType="application/octet-stream",Metadata={"sha256":ph})
                head=s3.head_object(Bucket=bucket(),Key=k)
                if head["ContentLength"]!=len(block) or head.get("Metadata",{}).get("sha256")!=ph:
                    raise RuntimeError("uploaded part verification failed: "+k)
                parts.append({"key":k,"size":len(block),"sha256":ph})
        manifest={"format":"hermes-dbbyte-backup-v1","backup_id":bid,"created_at":datetime.now(timezone.utc).isoformat(),
                  "encrypted_size":total,"encrypted_sha256":digest,"parts":parts}
        mk=prefix+"manifest.json"; body=json.dumps(manifest,separators=(",",":")).encode()
        s3.put_object(Bucket=bucket(),Key=mk,Body=body,ContentType="application/json")
        if s3.head_object(Bucket=bucket(),Key=mk)["ContentLength"]!=len(body): raise RuntimeError("manifest verification failed")
    log(f"verified encrypted backup {bid}; {total} bytes in {len(parts)} object(s)")
    # Delete old snapshots only after the new manifest and all parts are verified.
    for _,old in manifests(s3)[keep:]:
        oldprefix=old.rsplit("/",1)[0]+"/"; keys=[]
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket(),Prefix=oldprefix):
            keys.extend({"Key":x["Key"]} for x in page.get("Contents",[]))
        for n in range(0,len(keys),1000):
            s3.delete_objects(Bucket=bucket(),Delete={"Objects":keys[n:n+1000],"Quiet":True})
        log("pruned old snapshot "+oldprefix)
def restore_latest():
    required("HERMES_BACKUP_ENCRYPTION_PASSPHRASE")
    home=Path(os.environ.get("HERMES_HOME","/app/.cache/hermes-home"))
    state=home/"state.db"
    if state.exists() and state.stat().st_size>0:
        log("state.db already exists; skipping restore to protect existing data"); return
    s3=client(); found=manifests(s3)
    if not found: log("no remote backup found; first-time empty profile may start"); return
    mk=found[0][1]; m=json.loads(s3.get_object(Bucket=bucket(),Key=mk)["Body"].read())
    if m.get("format")!="hermes-dbbyte-backup-v1" or not m.get("parts"): raise RuntimeError("invalid backup manifest")
    with tempfile.TemporaryDirectory(prefix="hermes-restore-") as td:
        enc=Path(td)/"backup.aesgcm"; z=Path(td)/"backup.zip"; digest=hashlib.sha256()
        with open(enc,"wb") as out:
            for part in m["parts"]:
                data=s3.get_object(Bucket=bucket(),Key=part["key"])["Body"].read()
                if len(data)!=int(part["size"]) or hashlib.sha256(data).hexdigest()!=part["sha256"]:
                    raise RuntimeError("backup part integrity check failed: "+part["key"])
                out.write(data); digest.update(data)
        if enc.stat().st_size!=int(m["encrypted_size"]) or digest.hexdigest()!=m["encrypted_sha256"]:
            raise RuntimeError("encrypted archive checksum mismatch")
        decrypt(enc,z); check_zip(z)
        p=subprocess.run(["hermes","import",str(z),"--force"],cwd=home,env={**os.environ,"HOME":str(home)})
        if p.returncode: raise RuntimeError("Hermes import failed; refusing to continue with a partial restore")
    log("restored verified snapshot "+str(m.get("backup_id","unknown")))
def loop():
    delay=max(60,int(os.environ.get("HERMES_BACKUP_INITIAL_DELAY_SECONDS","60")))
    interval=max(3600,int(os.environ.get("HERMES_BACKUP_INTERVAL_SECONDS","86400")))
    log(f"backup service active; first backup in {delay}s; interval {interval}s")
    time.sleep(delay)
    while True:
        try: backup_once()
        except Exception as e: log(f"backup failed: {type(e).__name__}: {e}")
        time.sleep(interval)
def main():
    a=argparse.ArgumentParser(); a.add_argument("action",choices=["backup","restore","loop"]); x=a.parse_args()
    {"backup":backup_once,"restore":restore_latest,"loop":loop}[x.action]()
if __name__=="__main__":
    try: main()
    except Exception as e: log("FATAL: "+type(e).__name__+": "+str(e)); sys.exit(1)
