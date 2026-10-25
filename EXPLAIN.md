# Reading the code

These are useful checks when stepping through the experiment:

1. In `policy.py`, follow a valid request from signature verification to `effects.append`. Permission and freshness are separate checks even after authentication succeeds.
2. Trace two requests with the same ID. The replay check and insertion must share the lock; otherwise both could pass before either records the ID.
3. Check `future_nonce_retention` in the runner. Work through the timestamps before changing the 61-second retention period.
4. Check `rate_recovery_and_principal_isolation`. A rate rejection should allow a later retry, and Alice's request IDs shouldn't block Bob's.
5. Run `send_request.py` twice with the same ID, restart the server, and repeat. That demonstrates the in-memory state limitation directly.
6. Look at `url_00` through `url_10`. These are parser/admission cases. Nothing in the sink performs an outbound request.

To check that the runner notices a regression, temporarily change one expected response or remove the replay check. Run it, inspect the mismatch in the generated report, then restore the file.
