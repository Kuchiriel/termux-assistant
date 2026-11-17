---
name: disk-never-full
description: "Use to keep disk from ever filling (monitoring + thresholds + auto-response). Triggers: disk full, disk space, monitoring disk, cleanup automation."
license: MIT
---

# Disk Never Full (thresholds + actions)

- Monitor: `df` on /home + / daily (watcher or timer). Thresholds:
  80% = investigate (top offenders), 90% = act (caches/prune first),
  95% = stop writes (pause downloads/builds, escalate to owner).
- Auto-safe: docker builder prune, opencode tool-output >14d, capture
  PNGs >7d, npm/pip caches. All regenerable, all logged with df delta.
- NEVER auto: volumes, personal data, production datasets, credentials,
  anything referenced by config (models.nix refs decide for models).
- Weekly: git-orphan scan (`rev-list` vs `cat-file` counts) on big repos.
