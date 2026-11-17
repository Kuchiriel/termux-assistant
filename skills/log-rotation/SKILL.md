---
name: log-rotation
description: "Use when logs grow unbounded (app logs, session logs, tool outputs) — rotate, compress, prune with retention. Triggers: log growing, disk filling with logs, log management."
license: MIT
---

# Log Rotation

## When to Use This Skill
- A log file grows without bound across sessions
- `tool-output/`-style dirs accumulate GBs of truncated outputs
- Session logs (client-live, captures) pile in /tmp

## Process
1. **Classify**: active log (append-only, process holds fd) vs dead logs
   (finished sessions). NEVER truncate a file a live process writes
   without coordination (it keeps the offset — use copytruncate or
   restart the writer).
2. **Rotate**: `mv app.log app.log.$(date +%F) && touch app.log`
   (or `logrotate` with `copytruncate` for live writers).
3. **Compress**: `gzip` anything older than 2 days.
4. **Prune**: keep max 10 historical, delete older than 14 days.
5. **Verify**: writer still logging, `df` before/after, report freed.

## Don'ts
- Never `rm` the active log of a running service (use rotation).
- Never prune evidence involved in an open investigation.
