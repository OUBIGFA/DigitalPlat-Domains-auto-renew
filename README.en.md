# DigitalPlat Free Domain Auto Renew

This repository checks your DigitalPlat domains once per week. It only calls the DigitalPlat renewal API after a domain enters the free renewal window.

## Quick Setup

1. Create a DigitalPlat API key, usually starting with `dp_live_`:
   - https://dash.domain.digitalplat.org/dashboard/api/keys

2. Add this GitHub Actions secret:
   - `DIGITALPLAT_API_TOKEN`

3. Add this GitHub Actions variable:
   - `DIGITALPLAT_DOMAINS`

Use one domain per line:

```text
example.dpdns.org
example.qzz.io
```

Optional variable:

- `DIGITALPLAT_RENEW_BEFORE_DAYS`, default `120`

## Behavior

- Runs every Monday at 04:17 UTC.
- Checks all configured domains.
- Skips domains outside the renewal window.
- Renews with `renewal_type=free` and `years=1` after the window opens.
- Writes renewal/check state to `state/domains-state.json`.

## Local Dry Run

```powershell
$env:DIGITALPLAT_API_TOKEN='your_token'
$env:DIGITALPLAT_DOMAINS="example.dpdns.org`nexample.qzz.io"
python .\scripts\digitalplat_auto_renew.py --state .\state\domains-state.json --dry-run
```

## Files

- `scripts/digitalplat_auto_renew.py`
- `.github/workflows/digitalplat-auto-renew.yml`
- `state/domains-state.json`
