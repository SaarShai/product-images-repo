# Brainer Skills

The tracked `skills/` directory is canonical; `./install.sh` generates the `.claude`, `.codex`, and `.gemini` carrier catalogs.

```bash
./install.sh
python3 scripts/check_carrier_sync.py
```

The checker derives the tracked skill count and must report all three carriers
in sync; rerun `./install.sh` if a generated carrier drifts.
