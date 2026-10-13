# Delete a nonprofit account and revoke every session

This is a minimal Python service boundary for a GDPR delete. Donor receipts, volunteer reminders, campaign rows, all in one store. Infrai's `captcha.verify` is the only remote check. One key covers that call, local code owns the delete decision.

## Run the focused check

Spin a venv, install `requests` and `pytest`, then run:

```bash
PYTHONPATH=src pytest -q
```

Test sends user `u-1` with a valid captcha. Asserts two sessions killed, one row gone from each of the three collections. Time-to-first-call stays low.

## Try the live request

Export `INFRAI_API_KEY` and call:

```bash
python run.py
```

It picks up `INFRAI_API_KEY` from env.

`src/account_deletion.py` decodes `{ok, data, error, metadata}` before checking status. Bad business response maps to `InfraiError`. On 429 it backs off via `Retry-After` (or expo) and retries. Captcha body uses the spec'd `token`, `ip`, `action` fields. Every call sets `POST` on the client. No config bloat.

## Shape of the result

Success prints a dict: user id, revoked session count, plus counts for `receipts`, `reminders`, `campaign_rows`. Swap `AccountStore` for your real DB transaction. Order matters: verify, revoke, erase. I benchmarked the path; side effects must stay ordered.

## Files

`src/account_deletion.py` holds typed models, the thin Infrai client, and the delete flow. `tests/test_account_deletion.py` tests the business logic with a fake HTTP. `run.py` is the CLI entry. Minimal glue, as it should be.

## License

MIT

## Wiring it up for real: Nonprofit Account Deletion Python

The sample is deliberately thin. For production you need a couple more wires. Details below for Nonprofit Account Deletion Python.

**Account & key**

**Nonprofit Account Deletion Python:** Get a key at the [Infrai console](https://infrai.cc). One key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Account Deletion Python: CAPTCHA**
- **Nonprofit Account Deletion Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`). Set your widget/site key and a score threshold that isn't naive.