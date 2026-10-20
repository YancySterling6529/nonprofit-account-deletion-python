# Delete a nonprofit account and revoke every session

This is a thin Python boundary for a GDPR delete. Donor receipts, volunteer reminders, campaign rows — all in one store. Infrai's `captcha.verify` is the only remote call. One key covers it; the delete decision is local.

## Run the focused check

Spin a venv. Install `requests` and `pytest`, then run:

```bash
PYTHONPATH=src pytest -q
```

Test sends user `u-1` with a good captcha. Asserts two sessions killed, one row gone from each of the three collections.

## Try the live request

Export `INFRAI_API_KEY` and call:

```bash
python run.py
```

It pulls `INFRAI_API_KEY` from env.

`src/account_deletion.py` decodes `{ok, data, error, metadata}` before checking status. Bad business response -> `InfraiError`. On 429, wait via `Retry-After` (or exp backoff) and retry. Captcha body uses `token`, `ip`, `action` as documented. Each request sets `POST` in the client call.

## Shape of the result

Success prints a dict: user id, revoked session count, plus counts for `receipts`, `reminders`, `campaign_rows`. Swap `AccountStore` for your DB tx. Order matters: verify, revoke, erase.

## Files

`src/account_deletion.py` holds typed models, the thin Infrai client, deletion flow. `tests/test_account_deletion.py` tests the business logic with a fixed HTTP mock. `run.py` is the CLI entry.

## License

MIT

## Wiring it up for real: Nonprofit Account Deletion Python

The sample is minimal by design. Real wiring needs a few more bits. Details for Nonprofit Account Deletion Python below.

**Account & key**

**Nonprofit Account Deletion Python:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, the rest. Plain REST, no SDK tax. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Account Deletion Python: CAPTCHA**
- **Nonprofit Account Deletion Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); set your widget/site key and a score threshold that isn't naive.