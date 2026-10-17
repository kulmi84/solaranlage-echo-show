# Cloudflare relay

Setup and configuration: see the main [README](../README.md).

- `worker.mjs`: authenticated GET/POST endpoint at `/pv`.
- `schema.sql`: database schema for a new installation.
- `upgrade-solar.sql`: one-time migration for the earlier PV-only schema.
- `wrangler.example.jsonc`: copy locally to `wrangler.jsonc` and set your D1 ID.
- `worker.test.mjs`: authorization, data validation and storage tests.
- `check_relay.py`: read-only check using the ignored root `relay_config.json`.

The Worker retains one snapshot. POST and GET use separate encrypted secrets,
`WRITE_TOKEN` and `READ_TOKEN`. Its response includes server receipt time,
age, stale status, and Europe/Berlin date/time. Missing optional metrics are
stored as null. Request size is limited to 4096 bytes. All responses disable
caching and omit internal error details. No HA credentials belong here.

`upgrade-solar.sql` changes the database schema; apply it only to an existing
old database, before deploying the new Worker. Do not run it after `schema.sql`
on a new installation.
