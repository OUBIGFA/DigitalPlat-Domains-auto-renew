<div align="center">
  <h1>DigitalPlat Free Domain Auto Renew</h1>
  <p>Automatically check DigitalPlat domains weekly and renew them for free before expiry</p>
  <p><a href="README.md">简体中文</a> | English</p>
  <p>
    <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
    <img alt="Platform" src="https://img.shields.io/badge/platform-GitHub%20Actions-2088FF">
    <img alt="License" src="https://img.shields.io/badge/license-MIT-111827">
    <img alt="Schedule" src="https://img.shields.io/badge/schedule-Weekly-22c55e">
  </p>
</div>

> Deploy in 3 minutes. After that, it checks and renews your DigitalPlat free domains automatically every week.

## 3-Minute Deployment

### Step 0: Create a DigitalPlat API Token

Open:

- https://dash.domain.digitalplat.org/dashboard/api/keys

Create an API Key, typically starting with `dp_live_...`. Documentation:

- https://dash.domain.digitalplat.org/dashboard/api/docs

This project uses Bearer Token to call the DigitalPlat API.

### Step 1: Make the Repository Private

**1-1. Open GitHub Importer**

1. Sign in to GitHub.
2. Open: <https://github.com/new/import>

**1-2. Fill in import details**

| Field | Value |
| --- | --- |
| `Your old repository's clone URL` | `https://github.com/OUBIGFA/DigitalPlat-Domains-auto-renew` |
| `Owner` | Your GitHub account |
| `Repository name` | Your repo name, e.g. `my-digitalplat-auto-renew` |
| `Privacy` | Select `Private` |

Then click `Begin import`. It usually takes tens of seconds to a few minutes.

### Step 2: Configure GitHub Secret and Variable

Navigate to:

- `Settings -> Secrets and variables -> Actions`

Add a Secret:

- `DIGITALPLAT_API_TOKEN`

Add a Variable:

- `DIGITALPLAT_DOMAINS`

`DIGITALPLAT_DOMAINS` — one domain per line:

```text
example.dpdns.org
example.qzz.io
```

Optional Variable:

- `DIGITALPLAT_RENEW_BEFORE_DAYS`: default `120`

### Step 3: Run Once Manually

Go to the `Actions` tab in your GitHub repository and manually run `DigitalPlat Auto Renew`.

The first run checks the domains and generates `state/domains-state.json`. After that, the workflow runs automatically every Monday at UTC 04:17.

## Renewal Rules

Default rules:

- Free renewal window: `120` days before expiry
- Check once per week
- Renewal is only triggered when a domain enters the window
- Default: `renewal_type=free`, `years=1`

If a domain hasn't entered the renewal window yet, the script only logs the check status and does not call the renewal API.

## File Structure

- `scripts/digitalplat_auto_renew.py`: The renewal script
- `.github/workflows/digitalplat-auto-renew.yml`: Weekly GitHub Actions workflow
- `state/domains-state.json`: Auto-generated state file after execution

## API Reference

This implementation uses the DigitalPlat Domain API:

- `GET /domains`
- `GET /domains/{domain}`
- `POST /domains/{domain}/renew`

Default API Base:

- `https://domain-api.digitalplat.org/api/v1`

If the official documentation changes the API Base later, you can add `DIGITALPLAT_API_BASE` to GitHub Variables and update the workflow environment variable accordingly.

## License

This project is licensed under the MIT License.
