# Nightly schedule — how to enable (currently OFF)

The daily pipeline (`python -m src.pipeline`) runs collect -> triage -> match and
logs to `logs/newsletter.log`. It is **disabled** two ways right now:

1. `SCHEDULE_ENABLED=false` in `.env` — `python -m src.pipeline` is a no-op.
2. No OS scheduler entry is registered.

Nothing runs automatically until BOTH are turned on. Manual run any time:
`python -m src.pipeline --force`.

Dedup is guaranteed: collect inserts only new content hashes, triage only touches
untriaged rows, match is idempotent. Re-running never double-collects or re-charges.

---

## Enable later — Windows (dev box)

Register the task (runs `register_task.ps1`), then it still won't fire until you
also set `SCHEDULE_ENABLED=true` in `.env`:

```powershell
# from newsletter-service/
powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1
```

The script creates a DAILY 02:00 task named `TreppidesNewsletterDaily` and leaves
it **disabled**. Enable it in Task Scheduler (or `schtasks /Change /TN
TreppidesNewsletterDaily /ENABLE`) when ready.

## Enable later — server (Linux, production)

Prefer a systemd timer or cron. Cron line (02:00 nightly):

```
0 2 * * *  cd /path/to/newsletter-service && SCHEDULE_ENABLED=true .venv/bin/python -m src.pipeline
```

Or drop `SCHEDULE_ENABLED=true` in the service environment and run the bare command.
