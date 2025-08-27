# app/ml/upload_artifacts.py
import os
import pathlib
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_SERVICE_KEY"]
BUCKET        = os.getenv("SUPABASE_STORAGE_BUCKET", "artifacts")
VERSION       = os.getenv("MODEL_VERSION", "v1")
ART_DIR       = pathlib.Path("artifacts_local") / f"model_{VERSION}"

client = create_client(SUPABASE_URL, SUPABASE_KEY)

def ensure_bucket(bucket: str):
    try:
        client.storage.create_bucket(bucket, public=False)
        print(f"created bucket {bucket}")
    except Exception:
        # already exists
        pass

def upload_file(local_path: pathlib.Path, dest_path: str):
    data = local_path.read_bytes()
    # IMPORTANT: file_options values must be strings, not bools
    file_options = {
        "contentType": "application/octet-stream",
        "cacheControl": "3600",
        "upsert": "true",
    }
    resp = client.storage.from_(BUCKET).upload(dest_path, data, file_options)
    # storage3 returns None on success in some versions; just log path
    print("uploaded:", dest_path)

def main():
    if not ART_DIR.exists():
        raise SystemExit(f"Artifacts dir not found: {ART_DIR}")

    m = ART_DIR / "model.joblib"
    v = ART_DIR / "vectorizer.joblib"
    if not m.exists() or not v.exists():
        raise SystemExit(f"Missing artifacts in {ART_DIR}")

    ensure_bucket(BUCKET)

    base = f"model_{VERSION}"
    upload_file(m, f"{base}/model.joblib")
    upload_file(v, f"{base}/vectorizer.joblib")
    print("upload complete")

if __name__ == "__main__":
    main()

# add near the top, after load_dotenv()
print("SUPABASE_URL =", os.environ.get("SUPABASE_URL"))
k = os.environ.get("SUPABASE_SERVICE_KEY", "")
print("SERVICE_KEY head/tail/len:", k[:10], "...", k[-10:], "len=", len(k))

