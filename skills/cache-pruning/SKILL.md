---
name: cache-pruning
description: "Use when caches eat disk (HF hub, npm, docker builder, browser, nix store) — audit refs first, prune with the project's own tools. Triggers: cache full, HF cache huge, docker reclaimable, npm cache."
license: MIT
---

# Cache Pruning

## When to Use This Skill
- `~/.cache/huggingface` is GBs (audit `hub/models--*` refs FIRST —
  a 13GB cache was once 100% live models; never raw-rm `blobs/`).
- Docker reports reclaimable GBs (`docker system df`).
- npm/pip/chromium caches balloon.

## Process
1. **Audit**: list what's cached vs what's referenced (models.nix refs
   for GGUFs, hub repo list for HF, `docker system df` for builder).
2. **Project tools first**: `huggingface-cli delete-cache` (safe,
   ref-aware), `docker builder prune` (safe) / `image prune` (unused
   only), `npm cache clean --force`.
3. **Volumes NEVER blindly** (live DBs). `volume prune` only after
   listing + confirming detachment.
4. **Verify**: `df` before/after per target, report per-target freed.

## Don'ts
- Raw `rm -rf` on cache dirs (use the project's own prune commands).
- Pruning a cache a running job needs (check processes first).
