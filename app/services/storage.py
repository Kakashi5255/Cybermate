import os, io, joblib
from functools import lru_cache
from supabase import create_client

SUPABASE_URL  = os.getenv("SUPABASE_URL")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_KEY")
BUCKET        = os.getenv("SUPABASE_STORAGE_BUCKET", "artifacts")
VERSION       = os.getenv("MODEL_VERSION", "v1")
LOCAL_DIR     = os.getenv("LOCAL_ART_DIR", f"artifacts_local/model_{VERSION}")

@lru_cache(maxsize=1)
def load_artifacts():
    # Prefer local for dev speed
    if LOCAL_DIR and os.path.isdir(LOCAL_DIR):
        model = joblib.load(os.path.join(LOCAL_DIR, "model.joblib"))
        vect  = joblib.load(os.path.join(LOCAL_DIR, "vectorizer.joblib"))
        return model, vect

    # Fallback: download from Supabase Storage
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    base = f"model_{VERSION}"
    mbytes = client.storage.from_(BUCKET).download(f"{base}/model.joblib")
    vbytes = client.storage.from_(BUCKET).download(f"{base}/vectorizer.joblib")
    model = joblib.load(io.BytesIO(mbytes))
    vect  = joblib.load(io.BytesIO(vbytes))
    return model, vect
