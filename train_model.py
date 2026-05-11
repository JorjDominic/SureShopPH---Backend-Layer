"""
Train the fake-review classifier from a CSV file.

Usage:
    python train_model.py path/to/reviews.csv

The CSV must have columns: text, is_fake (0/1 or true/false)

Saves the trained pipeline to models/fake_review_model.pkl.
"""
from __future__ import annotations
import sys
import os


def main(csv_path: str) -> None:
    import pandas as pd
    import joblib
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score

    if not os.path.exists(csv_path):
        print(f"ERROR: file not found: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    if "text" not in df.columns or "is_fake" not in df.columns:
        print("ERROR: CSV must have columns: text, is_fake")
        sys.exit(1)

    df = df.dropna(subset=["text", "is_fake"])
    df["is_fake"] = df["is_fake"].astype(str).str.lower().isin(["1", "true", "yes"])

    if len(df) < 20:
        print(f"ERROR: need at least 20 samples, have {len(df)}")
        sys.exit(1)

    fake_count = int(df["is_fake"].sum())
    real_count = len(df) - fake_count
    if fake_count == 0 or real_count == 0:
        print("ERROR: need both fake and real samples")
        sys.exit(1)

    print(f"Training on {len(df)} samples (fake={fake_count}, real={real_count})...")

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            min_df=1,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])

    if len(df) >= 50:
        scores = cross_val_score(
            pipeline, df["text"].tolist(), df["is_fake"].astype(int).tolist(),
            cv=5, scoring="accuracy",
        )
        print(f"5-fold CV accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")

    pipeline.fit(df["text"].tolist(), df["is_fake"].astype(int).tolist())

    os.makedirs("models", exist_ok=True)
    out_path = os.path.join("models", "fake_review_model.pkl")
    joblib.dump(pipeline, out_path)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python train_model.py path/to/reviews.csv")
        sys.exit(1)
    main(sys.argv[1])
