# SureShopPH Backend Layer

FastAPI backend for the SureShopPH browser extension — analyzes
Filipino e-commerce listings (Shopee, Lazada, Facebook Marketplace)
and returns a risk score plus confidence rating.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Optional — calamanCy Tagalog model
python -m spacy download tl_calamancy_md
# (or: pip install https://huggingface.co/ljvmiranda921/tl_calamancy_md/...)
```

Copy `.env.example` to `.env` and fill in:

```
SUPABASE_URL=...
SUPABASE_KEY=...      # service role key
JWT_SECRET=...        # Supabase project's JWT secret
ENABLE_GROQ_COMMENT_SUMMARY=false
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TIMEOUT_SECONDS=8
```

Run the SQL in `supabase_schema.sql` against your Supabase project to
create the new tables and RLS policies. The existing `profiles` table
is referenced as-is.

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Base URL: `http://localhost:8000` — interactive docs at `/docs`.

## Endpoints

| Method | Path                    | Auth   | Purpose                       |
|--------|-------------------------|--------|-------------------------------|
| POST   | /analyze/listing        | user   | Normal scan                   |
| POST   | /analyze/comments       | user   | Comments-only scan            |
| POST   | /analyze/deep           | user   | Listing + comments combined   |
| POST   | /analyze/url            | user   | URL safety check              |
| GET    | /scans/history          | user   | Caller's scan history         |
| GET    | /listings/high-risk     | user   | Public high-risk listings     |
| POST   | /reports                | user   | Submit false-positive report  |
| GET    | /admin/reports          | admin  | All user reports              |
| PATCH  | /admin/listings/verify  | admin  | Verify a high-risk listing    |
| GET    | /admin/logs             | admin  | Admin audit log               |
| POST   | /admin/logs             | admin  | Append admin log entry        |

All endpoints require `Authorization: Bearer <supabase_jwt>`.
Admin endpoints additionally require `profiles.role == "admin"`.

## ML model

Place a trained sklearn pipeline at `models/fake_review_model.pkl`.
If absent the classifier falls back to deterministic rules. The
pipeline must accept raw strings (e.g. `Pipeline([Tfidf, RandomForest])`)
and expose `predict_proba` with class 1 = fake.

## Notes

- Listing and comment data are analyzed in-memory and discarded —
  only metadata (URL, score, flags) is persisted.
- The system never claims confirmed fraud; outputs are probabilistic
  estimates of observable risk signals.
