# app/ml/train_scambot.py
# Robust training script: reads messy CSVs, normalises text, trains TF-IDF + Logistic Regression,
# and saves vectorizer/model as joblib artifacts.

import os, re, unicodedata, joblib, pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, precision_recall_fscore_support

# ---------- config ----------
DATA_PATH   = os.getenv("SCAMBOT_DATA", "Data/super_sms_dataset.csv")
OUT_DIR     = Path("artifacts_local/model_v1")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 42

# ---------- utilities ----------
SMART_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201A": ",", "\u201B": "'",
    "\u201C": '"', "\u201D": '"', "\u201E": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",  # en/em dash, minus
}
CTRL_RE = re.compile(r"[\u0000-\u001F\u007F-\u009F]")  # control ranges

def normalise_text(s: str) -> str:
    """Lowercase, normalize Unicode, map smart punctuation, drop control chars, collapse spaces."""
    if not isinstance(s, str):
        return ""
    s = s.replace("\ufeff", "").replace("\u200b", "")       # BOM/zero-width
    s = unicodedata.normalize("NFKC", s)                    # Unicode normalization
    for k, v in SMART_MAP.items():
        s = s.replace(k, v)                                  # smart quotes/dashes -> ASCII
    s = CTRL_RE.sub(" ", s)                                  # remove control chars
    s = re.sub(r"\s+", " ", s).strip().lower()               # trim + lowercase
    return s

def pick_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"Expected one of {candidates}, got {list(df.columns)}")

def robust_read_csv(path: str) -> pd.DataFrame:
    """Read messy CSVs: try UTF-8 (with replacement), fall back to cp1252; skip bad lines."""
    try:
        return pd.read_csv(
            path,
            encoding="utf-8",
            encoding_errors="replace",   # keep going if bytes are invalid
            engine="python",
            on_bad_lines="skip",
        )
    except UnicodeDecodeError:
        print("UTF-8 failed; retrying with cp1252")
        return pd.read_csv(
            path,
            encoding="cp1252",
            encoding_errors="replace",
            engine="python",
            on_bad_lines="skip",
        )

# ---------- load ----------
print(f"Loading {DATA_PATH}")
df = robust_read_csv(DATA_PATH)
print(f"Loaded {len(df):,} rows with columns: {list(df.columns)}")

text_col  = pick_col(df, ["sms_text","text","message","SMSes","sms","content"])
label_col = pick_col(df, ["label_binary","label","Labels","target","is_spam","spam"])

df[text_col] = df[text_col].astype(str).map(normalise_text)

# normalise labels to {0,1}
y = df[label_col]
if y.dtype == "O":
    y = y.str.lower().map({"spam":1, "scam":1, "ham":0, "legit":0})
y = pd.to_numeric(y, errors="coerce").fillna(0).astype(int)
X = df[text_col]

# ---------- split ----------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
)

# ---------- vectoriser ----------
vectorizer = TfidfVectorizer(
    ngram_range=(1,2),           # unigrams + bigrams
    min_df=2,                    # ignore tokens seen once
    max_df=0.98,                 # drop extremely common tokens
    lowercase=True,
    strip_accents="unicode",
    sublinear_tf=True
)
Xtr = vectorizer.fit_transform(X_train)
Xte = vectorizer.transform(X_test)

# ---------- model ----------
clf = LogisticRegression(
    solver="liblinear",          # good for sparse TF-IDF
    class_weight="balanced",     # safer under class imbalance
    max_iter=500,
    random_state=RANDOM_STATE
)
clf.fit(Xtr, y_train)

# ---------- evaluation ----------
y_pred = clf.predict(Xte)
print("\n=== Classification report (positive class = 1) ===")
print(classification_report(y_test, y_pred, digits=3))
p, r, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", zero_division=0)
print({"precision_pos": round(p,3), "recall_pos": round(r,3), "f1_pos": round(f1,3)})

# ---------- save artifacts ----------
joblib.dump(vectorizer, OUT_DIR / "vectorizer.joblib")
joblib.dump(clf,         OUT_DIR / "model.joblib")
print(f"\nSaved artifacts to: {OUT_DIR.resolve()}")
