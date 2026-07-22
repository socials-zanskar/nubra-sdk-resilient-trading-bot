# Nubra SDK — A Resilient End-to-End Trading Script (Python)

A complete, realistic template for the **Nubra Python SDK** (`nubra-sdk`) that puts all the error handling together in one flow:

```
login → look up instrument → place order → check order status
```

Every step handles its own failures, logs what happened, and exits cleanly instead of crashing with a raw traceback.

## What each step demonstrates

| Step | Error handling shown |
|---|---|
| **Login** | Catches `ValueError` from OTP/MPIN failures ("Maximum OTP attempts exceeded") |
| **Instrument lookup** | Lookups don't raise — they return `{"msg": ...}` when not found; the code checks for it |
| **Place order** | Catches `NubraValidationError`, `UnauthorizedError`, `BadRequestError`, `ServerError`, `RetryLimitExceeded` — each with the right response |
| **Check status** | Retries reads (safe) with a wait between attempts |
| **Whole script** | Top-level `NubraHttpError` safety net + graceful Ctrl+C |

## Logging instead of print

The SDK logs internally but stays silent by default. One line turns its logs on alongside yours:

```python
logging.basicConfig(level=logging.INFO)
```

Switch to `level=logging.DEBUG` when investigating a problem.

## Golden rules used in this template

1. **Validation errors** → fix the payload, never retry as-is
2. **Rejections (4xx)** → read the reason, fix the cause
3. **Network/server errors** → retry reads freely; for orders, check `trader.orders()` first to avoid duplicates
4. **Auth errors** → the SDK already re-logged-in once; if you still see `UnauthorizedError`, delete `auth_data.db` and log in fresh

## Run it

```bash
pip install -r requirements.txt
python main.py
```

⚠️ This script places a **real order** (1 share of RELIANCE, intraday, market price) when run against `PROD`. Change the symbol/qty or use a test environment first.
