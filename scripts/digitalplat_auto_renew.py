#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_BASE = "https://domain-api.digitalplat.org/api/v1"
DATE_FORMAT = "%Y-%m-%d"
DEFAULT_RENEW_BEFORE_DAYS = 120


@dataclass
class DomainRecord:
    name: str
    raw: dict[str, Any]
    expiry_date: datetime
    status: str | None
    can_renew: bool | None

    @property
    def days_remaining(self) -> int:
        now = datetime.now(timezone.utc)
        return (self.expiry_date.date() - now.date()).days


class DigitalPlatClient:
    def __init__(self, api_token: str, api_base: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "digitalplat-auto-renew/1.0",
        }

    def _request(
        self,
        path: str,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=body,
            headers=self.headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DigitalPlat HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"DigitalPlat network error: {exc}") from exc

        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"DigitalPlat returned non-JSON response: {text[:200]}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError(f"DigitalPlat returned unexpected response: {parsed}")
        return parsed

    def list_domains(self) -> list[dict[str, Any]]:
        data = self._request("/domains")
        payload = unwrap_response(data)
        domains = payload.get("domains") if isinstance(payload, dict) else payload
        if not isinstance(domains, list):
            raise RuntimeError(f"DigitalPlat domain list response is missing domains: {data}")
        return [item for item in domains if isinstance(item, dict)]

    def get_domain(self, domain: str) -> dict[str, Any]:
        encoded = urllib.parse.quote(domain, safe="")
        data = self._request(f"/domains/{encoded}")
        payload = unwrap_response(data)
        record = payload.get("domain", payload) if isinstance(payload, dict) else None
        if not isinstance(record, dict):
            raise RuntimeError(f"DigitalPlat domain detail response is missing domain: {data}")
        return record

    def renew_domain(self, domain: str, renewal_type: str, years: int) -> dict[str, Any]:
        encoded = urllib.parse.quote(domain, safe="")
        data = self._request(
            f"/domains/{encoded}/renew",
            method="POST",
            payload={"renewal_type": renewal_type, "years": years},
        )
        payload = unwrap_response(data)
        record = payload.get("domain", payload) if isinstance(payload, dict) else None
        if not isinstance(record, dict):
            raise RuntimeError(f"DigitalPlat renewal response is unexpected: {data}")
        return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly DigitalPlat free-domain renewal helper.")
    parser.add_argument("--state", default="state/domains-state.json", help="Path to state JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate without renewing or writing state.")
    parser.add_argument("--fixture", help="Read a local DigitalPlat domain-list JSON fixture instead of calling the API.")
    return parser.parse_args()


def unwrap_response(data: dict[str, Any]) -> Any:
    if "success" in data and data.get("success") is False:
        message = data.get("error") or data.get("message") or data
        raise RuntimeError(f"DigitalPlat API returned an error: {message}")
    if "data" in data:
        return data["data"]
    return data


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def optional_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc


def parse_domain_variable() -> list[str]:
    raw = require_env("DIGITALPLAT_DOMAINS")
    normalized = raw.replace(",", "\n")
    domains = [line.strip().lower() for line in normalized.splitlines() if line.strip()]
    if not domains:
        raise RuntimeError("DIGITALPLAT_DOMAINS is empty.")
    duplicates = sorted({domain for domain in domains if domains.count(domain) > 1})
    if duplicates:
        raise RuntimeError(f"DIGITALPLAT_DOMAINS contains duplicates: {', '.join(duplicates)}")
    return domains


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"domains": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_datetime(value: Any) -> datetime:
    if not value:
        raise ValueError("empty date")
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc)
    if len(text) == 10:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Unsupported date format: {value}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def pick_first(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return None


def normalize_domain(raw: dict[str, Any]) -> DomainRecord:
    name = pick_first(raw, ("domain", "name", "full_domain"))
    if not name:
        raise RuntimeError(f"Domain record is missing a domain name: {raw}")
    expiry = pick_first(raw, ("expiry_date", "expires_at", "expiryDate", "expiresAt", "expiration_date"))
    if not expiry:
        raise RuntimeError(f"Domain record is missing expiry_date: {raw}")
    can_renew = pick_first(raw, ("can_free_renew", "can_renew", "renewable"))
    if isinstance(can_renew, str):
        can_renew = can_renew.strip().lower() in ("1", "true", "yes", "y")
    elif can_renew is not None:
        can_renew = bool(can_renew)
    return DomainRecord(
        name=str(name).strip().lower(),
        raw=raw,
        expiry_date=parse_datetime(expiry),
        status=None if raw.get("status") is None else str(raw.get("status")),
        can_renew=can_renew,
    )


def load_fixture(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = unwrap_response(data)
    if isinstance(data, dict):
        domains = data.get("domains")
        if isinstance(domains, list):
            return [item for item in domains if isinstance(item, dict)]
        domain = data.get("domain")
        if isinstance(domain, dict):
            return [domain]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    raise RuntimeError(f"Fixture must contain a domains list or domain object: {path}")


def should_renew(record: DomainRecord, renew_before_days: int) -> bool:
    if record.can_renew is False:
        return False
    return record.days_remaining <= renew_before_days


def update_state_for_record(
    state: dict[str, Any],
    record: DomainRecord,
    action: str,
    renew_before_days: int,
) -> bool:
    domains = state.setdefault("domains", {})
    item = domains.setdefault(record.name, {})
    new_item = {
        "expiry_date": record.expiry_date.strftime(DATE_FORMAT),
        "days_remaining": record.days_remaining,
        "renew_before_days": renew_before_days,
        "status": record.status,
        "last_action": action,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    changed = False
    for key, value in new_item.items():
        if item.get(key) != value:
            item[key] = value
            changed = True
    return changed


def remove_stale_domains(state: dict[str, Any], active_domains: set[str]) -> bool:
    domains = state.setdefault("domains", {})
    stale = [domain for domain in domains if domain not in active_domains]
    for domain in stale:
        del domains[domain]
    return bool(stale)


def main() -> int:
    args = parse_args()
    state_path = Path(args.state).resolve()
    managed_names = parse_domain_variable()
    renew_before_days = optional_int_env("DIGITALPLAT_RENEW_BEFORE_DAYS", DEFAULT_RENEW_BEFORE_DAYS)
    renewal_type = os.getenv("DIGITALPLAT_RENEWAL_TYPE") or "free"
    renewal_years = optional_int_env("DIGITALPLAT_RENEWAL_YEARS", 1)

    client: DigitalPlatClient | None = None
    if args.fixture:
        raw_domains = load_fixture(Path(args.fixture))
    else:
        token = require_env("DIGITALPLAT_API_TOKEN")
        api_base = os.getenv("DIGITALPLAT_API_BASE") or API_BASE
        client = DigitalPlatClient(token, api_base)
        raw_domains = client.list_domains()

    domain_map = {normalize_domain(raw).name: raw for raw in raw_domains}
    state = load_state(state_path)
    state_changed = remove_stale_domains(state, set(managed_names))
    renewed_count = 0
    errors: list[str] = []

    print(f"UTC now: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"Renewal window: {renew_before_days} day(s) before expiry")

    for domain in managed_names:
        raw = domain_map.get(domain)
        if raw is None and client is not None:
            try:
                raw = client.get_domain(domain)
            except Exception as exc:
                errors.append(f"{domain}: failed to fetch detail: {exc}")
                continue
        if raw is None:
            errors.append(f"{domain}: not found in DigitalPlat account")
            continue

        try:
            record = normalize_domain(raw)
        except Exception as exc:
            errors.append(f"{domain}: failed to parse domain record: {exc}")
            continue

        print(
            f"[CHECK] {record.name} expiry_date={record.expiry_date.strftime(DATE_FORMAT)} "
            f"days_remaining={record.days_remaining} status={record.status or '-'}"
        )

        if not should_renew(record, renew_before_days):
            print(f"[SKIP] {record.name} has not entered the renewal window.")
            state_changed = update_state_for_record(state, record, "skipped", renew_before_days) or state_changed
            continue

        if args.dry_run:
            print(f"[DRY-RUN] Would renew {record.name} with renewal_type={renewal_type} years={renewal_years}.")
            continue

        if client is None:
            print(f"[FIXTURE] Would renew {record.name}.")
            continue

        try:
            renewed_raw = client.renew_domain(record.name, renewal_type, renewal_years)
            renewed_record = normalize_domain(renewed_raw)
        except Exception as exc:
            errors.append(f"{record.name}: renewal failed: {exc}")
            state_changed = update_state_for_record(state, record, "renew_failed", renew_before_days) or state_changed
            continue

        renewed_count += 1
        state_changed = update_state_for_record(state, renewed_record, "renewed", renew_before_days) or state_changed
        print(
            f"[RENEWED] {renewed_record.name} new_expiry_date={renewed_record.expiry_date.strftime(DATE_FORMAT)} "
            f"days_remaining={renewed_record.days_remaining}"
        )

    if state_changed and not args.dry_run:
        save_state(state_path, state)
        print(f"[WRITE] Updated {state_path}")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        return 1

    if renewed_count == 0:
        print("[DONE] No domains were renewed in this run.")
    else:
        print(f"[DONE] Renewed {renewed_count} domain(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        raise
