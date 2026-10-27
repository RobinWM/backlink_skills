#!/usr/bin/env python3
"""Directory Admin API helpers for Shipmore directory metadata sync.

Auth: prefer personal dashboard API key via SHIPMORE_API_KEY + x-api-key
(same key shape as Queue). Shared DIRECTORY_ADMIN_API_TOKEN is deprecated
pending ShipMore Admin redesign (personal keys + server-side admin-role checks).
Never print the API key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_UNAVAILABLE_STREAK_ROOT = Path.home() / '.shipmore' / 'directory-unavailable'
UNAVAILABLE_REJECT_THRESHOLD = 3

DIRECTORY_PRICING = ('free', 'paid', 'backlink')
# When a page offers more than one listing path, observe the highest-priority one.
# Apply only after each path is classified correctly: true free (no badge /
# reciprocal / backlink requirement) beats backlink-as-price, which beats
# cash-only paid tiers. A Free/$0 label that still requires badge/reciprocal/
# backlink is classified as backlink first, so it cannot falsely win as free.
OBSERVED_PRICING_PRIORITY = ('free', 'backlink', 'paid')
DIRECTORY_STATUSES = ('active', 'pending', 'rejected')

# Tokens that mean the usable listing path's price is a link/badge, not cash-free.
_BACKLINK_COST_TOKENS = frozenset(
    {
        'badge',
        'badges',
        'reciprocal',
        'backlink',
        'backlinks',
        'linkback',
        'linkbacks',
    }
)

SHIPMORE_API_KEY_ENV = 'SHIPMORE_API_KEY'
# Deprecated shared admin secret; do not document minting new values.
_DEPRECATED_ADMIN_TOKEN_ENV = 'DIRECTORY_ADMIN_API_TOKEN'
UNAVAILABLE_STREAK_DIR_ENV = 'SHIPMORE_DIRECTORY_UNAVAILABLE_DIR'
_ADMIN_DEPRECATION_WARNED = False


class DirectoryAdminError(RuntimeError):
    pass


def env(name: str, fallback: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return fallback
    return value.strip()


def require(value: str | None, message: str) -> str:
    if value is None or not value.strip():
        raise DirectoryAdminError(message)
    return value.strip()


def resolve_admin_api_key(explicit: str | None = None) -> str | None:
    """Resolve Admin auth: SHIPMORE_API_KEY first; deprecated env only as fallback.

    Never print the key. Soft Admin paths treat a missing key as non-blocking.
    """
    global _ADMIN_DEPRECATION_WARNED
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    primary = env(SHIPMORE_API_KEY_ENV)
    if primary:
        return primary
    legacy = env(_DEPRECATED_ADMIN_TOKEN_ENV)
    if legacy:
        if not _ADMIN_DEPRECATION_WARNED:
            print(
                (
                    f'WARNING: {_DEPRECATED_ADMIN_TOKEN_ENV} is deprecated. '
                    f'Use personal dashboard API key via {SHIPMORE_API_KEY_ENV} '
                    f'and header x-api-key. Shared Directory Admin secrets are '
                    f'being removed; ShipMore Admin will check admin role server-side.'
                ),
                file=sys.stderr,
            )
            _ADMIN_DEPRECATION_WARNED = True
        return legacy
    return None


def sanitize_directory_id(directory_id: str) -> str:
    value = require(directory_id, 'directoryId is required')
    if any(ch in value for ch in ('/', '\\', '\0')):
        raise DirectoryAdminError('directoryId must not contain path separators')
    return value


def _normalize_observation_text(observation: str) -> str:
    """Normalize one live-path phrase for alias / cost-token matching."""
    raw = require(observation, 'observed pricing text is required').strip().lower()
    # Treat +, /, & as separators so "free+badge" / "free & badge" tokenize.
    for ch in ('+', '/', '&'):
        raw = raw.replace(ch, ' ')
    # Drop currency markers so "$0" / "€0" collapse like free labels.
    for ch in ('$', '€', '£'):
        raw = raw.replace(ch, ' ')
    # Normalize "free listing" / "free-listing" / "free_listing" to one key form.
    return '_'.join(raw.replace('-', ' ').replace('_', ' ').split())


def _observation_tokens(normalized: str) -> list[str]:
    return [token for token in normalized.split('_') if token]


def _has_backlink_listing_cost(normalized: str) -> bool:
    """True when this single path requires badge / reciprocal / backlink."""
    tokens = _observation_tokens(normalized)
    if any(token in _BACKLINK_COST_TOKENS for token in tokens):
        return True
    # "link back" / "link_back" after normalization.
    for index in range(len(tokens) - 1):
        if tokens[index] == 'link' and tokens[index + 1] == 'back':
            return True
    return False


def map_observed_pricing(observation: str) -> str:
    """Map one free-text live-site path into directoryPricing enum.

    Classification (per path, before multi-path priority):
    - Requires badge / reciprocal / backlink (even if labeled Free / $0)
      → ``backlink`` — never ``free``.
    - True ``free`` = no cash payment AND no badge/reciprocal/backlink requirement.
    - Cash-only paid / expedite tiers → ``paid``.

    For pages that offer multiple paths, use resolve_observed_pricing() so the
    priority free > backlink > paid is applied to correctly classified paths.
    """
    text = _normalize_observation_text(observation)
    aliases = {
        'free': 'free',
        'free_listing': 'free',
        'free_queue': 'free',
        'free_submit': 'free',
        '0': 'free',
        'paid': 'paid',
        'paid_only': 'paid',
        'expedite': 'paid',
        'paid_tier': 'paid',
        'paid_tiers': 'paid',
        'backlink': 'backlink',
        'reciprocal': 'backlink',
        'reciprocal_link': 'backlink',
        'reciprocal_backlink': 'backlink',
        'badge': 'backlink',
        'badge_required': 'backlink',
        'link_back': 'backlink',
    }
    # Exact aliases first (including pure badge/reciprocal/backlink tokens).
    if text in aliases:
        mapped = aliases[text]
        # Defensive: never let a Free/$0+badge compound alias slip through as free.
        if mapped == 'free' and _has_backlink_listing_cost(text):
            return 'backlink'
        return mapped
    if text in DIRECTORY_PRICING:
        return text
    # Compound single-path wording: "free with badge", "$0 badge required", etc.
    if _has_backlink_listing_cost(text):
        return 'backlink'
    raise DirectoryAdminError(
        f'Unsupported observed pricing "{observation}"; '
        f'expected one of {", ".join(DIRECTORY_PRICING)} or a documented alias'
    )


def _split_observed_pricing_inputs(
    observations: str | list[str] | tuple[str, ...],
) -> list[str]:
    if isinstance(observations, str):
        parts = [part.strip() for part in observations.split(',')]
        return [part for part in parts if part]
    if isinstance(observations, (list, tuple)):
        parts: list[str] = []
        for item in observations:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            if ',' in text:
                parts.extend(_split_observed_pricing_inputs(text))
            else:
                parts.append(text)
        return parts
    raise DirectoryAdminError('observed pricing must be a string or list of strings')


def resolve_observed_pricing(
    observations: str | list[str] | tuple[str, ...],
) -> str:
    """Collapse one or more live paths to a single directoryPricing enum.

    Classify each path first (see map_observed_pricing): a Free/$0 path that
    still requires badge / reciprocal / backlink is ``backlink``, not ``free``.
    Only then apply multi-path priority **free > backlink > paid**:
    - a true free path (no payment, no badge/reciprocal/backlink) → `free`
      (wins even if paid expedite or separate backlink options exist)
    - else a reciprocal/backlink/badge path (incl. $0+badge) → `backlink`
      (wins even if paid tiers exist)
    - else only paid paths → `paid`
    """
    parts = _split_observed_pricing_inputs(observations)
    if not parts:
        raise DirectoryAdminError('at least one observed pricing path is required')
    mapped = {map_observed_pricing(part) for part in parts}
    for candidate in OBSERVED_PRICING_PRIORITY:
        if candidate in mapped:
            return candidate
    raise DirectoryAdminError(
        f'Unable to resolve observed pricing from {sorted(mapped)!r}'
    )


def admin_sync_note(kind: str, *, ok: bool, status_code: int | None = None) -> str:
    """Human-readable non-secret note for exactResult / followUpNote (Brennan).

    Format: 具体原因【报错信息】 when a raw status/detail exists; human reason only
    otherwise. Never includes secrets.
    """
    subject = {'pricing': '定价', 'status': '状态'}.get(kind, kind)
    if ok:
        return f'Admin {subject}同步成功'
    if status_code is None:
        return f'Admin {subject}同步失败【缺少 API key 或网络错误】'
    return f'Admin {subject}同步失败【HTTP {status_code}】'


def _streak_root() -> Path:
    return Path(
        env(UNAVAILABLE_STREAK_DIR_ENV, str(DEFAULT_UNAVAILABLE_STREAK_ROOT))
        or str(DEFAULT_UNAVAILABLE_STREAK_ROOT)
    ).expanduser()


def _streak_path(directory_id: str) -> Path:
    digest = hashlib.sha256(sanitize_directory_id(directory_id).encode('utf-8')).hexdigest()[
        :32
    ]
    return _streak_root() / f'{digest}.json'


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp = path.with_suffix(f'.{os.getpid()}.tmp')
    with open(temp, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(',', ':'))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    os.replace(temp, path)


def read_local_unavailable_streak(directory_id: str) -> int:
    path = _streak_path(directory_id)
    if not path.exists():
        return 0
    try:
        with open(path, encoding='utf-8') as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        count = int(payload.get('consecutiveUnavailable', 0))
    except (TypeError, ValueError):
        return 0
    return max(0, count)


def write_local_unavailable_streak(directory_id: str, count: int) -> dict[str, Any]:
    safe_id = sanitize_directory_id(directory_id)
    payload = {
        'directoryId': safe_id,
        'consecutiveUnavailable': max(0, int(count)),
        'updatedAtEpoch': int(time.time()),
    }
    _atomic_write(_streak_path(safe_id), payload)
    return payload


def resolve_consecutive_unavailable(
    directory_id: str,
    *,
    shipmore_consecutive_count: int | None = None,
) -> int:
    """Prefer Shipmore-backed consecutive unavailable count when provided."""
    if shipmore_consecutive_count is not None:
        try:
            count = int(shipmore_consecutive_count)
        except (TypeError, ValueError) as exc:
            raise DirectoryAdminError(
                'shipmore consecutive unavailable count must be an integer'
            ) from exc
        if count < 0:
            raise DirectoryAdminError(
                'shipmore consecutive unavailable count must be >= 0'
            )
        write_local_unavailable_streak(directory_id, count)
        return count
    return read_local_unavailable_streak(directory_id)


def record_unavailable_outcome(
    directory_id: str,
    *,
    shipmore_consecutive_count: int | None = None,
) -> dict[str, Any]:
    """Increment or adopt Shipmore streak; return whether reject threshold is met."""
    if shipmore_consecutive_count is not None:
        count = resolve_consecutive_unavailable(
            directory_id,
            shipmore_consecutive_count=shipmore_consecutive_count,
        )
    else:
        count = read_local_unavailable_streak(directory_id) + 1
        write_local_unavailable_streak(directory_id, count)
    return {
        'directoryId': sanitize_directory_id(directory_id),
        'consecutiveUnavailable': count,
        'shouldRejectDirectory': count >= UNAVAILABLE_REJECT_THRESHOLD,
        'threshold': UNAVAILABLE_REJECT_THRESHOLD,
        'source': 'shipmore' if shipmore_consecutive_count is not None else 'local',
    }


def reset_unavailable_streak(directory_id: str) -> dict[str, Any]:
    payload = write_local_unavailable_streak(directory_id, 0)
    return {
        'directoryId': payload['directoryId'],
        'consecutiveUnavailable': 0,
        'shouldRejectDirectory': False,
        'threshold': UNAVAILABLE_REJECT_THRESHOLD,
        'source': 'local',
    }


class DirectoryAdminClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = require(api_key, f'Missing ShipMore API key. Set {SHIPMORE_API_KEY_ENV}.')
        self.timeout = timeout

    @property
    def directories_url(self) -> str:
        return f'{self.base_url}/api/admin/directories'

    @property
    def directories_status_url(self) -> str:
        return f'{self.base_url}/api/admin/directories/status'

    def auth_headers(self) -> dict[str, str]:
        """Personal API key header; matches Queue/outbound-links auth shape."""
        return {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'shipmore-directory-admin-skill/1.0',
        }

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        request = Request(
            url,
            data=body,
            method=method,
            headers=self.auth_headers(),
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                status_code = getattr(response, 'status', None) or response.getcode()
                raw = response.read().decode('utf-8')
        except HTTPError as exc:
            raw = exc.read().decode('utf-8', errors='replace')
            try:
                error_body = json.loads(raw) if raw else {'raw': raw}
            except json.JSONDecodeError:
                error_body = {'raw': raw}
            return {
                'ok': False,
                'statusCode': exc.code,
                'error': error_body,
            }
        except URLError as exc:
            return {
                'ok': False,
                'statusCode': None,
                'error': {'reason': str(exc.reason)},
            }

        parsed: Any
        if raw.strip():
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {'raw': raw}
        else:
            parsed = {}

        return {
            'ok': 200 <= int(status_code) < 300,
            'statusCode': int(status_code),
            'data': parsed,
        }

    def update_directory(
        self,
        directory_id: str,
        *,
        pricing: str | None = None,
        status: str | None = None,
        rejected_reason: str | None = None,
        dofollow: bool | None = None,
    ) -> dict[str, Any]:
        safe_id = sanitize_directory_id(directory_id)
        payload: dict[str, Any] = {'directoryId': safe_id}
        if pricing is not None:
            pricing_value = pricing.strip().lower()
            if pricing_value not in DIRECTORY_PRICING:
                raise DirectoryAdminError(
                    f'pricing must be one of {", ".join(DIRECTORY_PRICING)}'
                )
            payload['pricing'] = pricing_value
        if status is not None:
            status_value = status.strip().lower()
            if status_value not in DIRECTORY_STATUSES:
                raise DirectoryAdminError(
                    f'status must be one of {", ".join(DIRECTORY_STATUSES)}'
                )
            payload['status'] = status_value
        if rejected_reason is not None and rejected_reason.strip():
            payload['rejectedReason'] = rejected_reason.strip()
        if dofollow is not None:
            payload['dofollow'] = bool(dofollow)
        if set(payload.keys()) == {'directoryId'}:
            raise DirectoryAdminError(
                'update_directory requires at least one of pricing, status, '
                'rejectedReason, or dofollow'
            )
        result = self._request('PATCH', self.directories_url, payload)
        result['endpoint'] = 'directories'
        result['directoryId'] = safe_id
        result['note'] = admin_sync_note(
            'pricing' if 'pricing' in payload and 'status' not in payload else 'directory',
            ok=bool(result.get('ok')),
            status_code=result.get('statusCode'),
        )
        return result

    def update_directory_status(
        self,
        directory_id: str,
        status: str,
    ) -> dict[str, Any]:
        safe_id = sanitize_directory_id(directory_id)
        status_value = require(status, 'status is required').strip().lower()
        if status_value not in DIRECTORY_STATUSES:
            raise DirectoryAdminError(
                f'status must be one of {", ".join(DIRECTORY_STATUSES)}'
            )
        result = self._request(
            'PATCH',
            self.directories_status_url,
            {'directoryId': safe_id, 'status': status_value},
        )
        result['endpoint'] = 'directories/status'
        result['directoryId'] = safe_id
        result['note'] = admin_sync_note(
            'status',
            ok=bool(result.get('ok')),
            status_code=result.get('statusCode'),
        )
        return result


def sync_pricing_if_mismatch(
    client: DirectoryAdminClient | None,
    *,
    directory_id: str,
    claim_pricing: str,
    observed_pricing: str,
) -> dict[str, Any]:
    """PATCH pricing when live observation disagrees with claim snapshot.

    Admin sync is additive: callers still complete the Run Item with the usual
    submission status (e.g. paid_only). Missing token / non-2xx does not raise;
    returns a non-secret note for exactResult/followUpNote.
    """
    claim = require(claim_pricing, 'claim directoryPricing is required').strip().lower()
    # Accept a single enum/alias or multiple paths (list / comma-separated).
    # Each path is classified first ($0+badge → backlink); then multi-path
    # pages resolve with free > backlink > paid.
    observed = resolve_observed_pricing(observed_pricing)
    if claim not in DIRECTORY_PRICING:
        raise DirectoryAdminError(
            f'claim directoryPricing must be one of {", ".join(DIRECTORY_PRICING)}'
        )
    if claim == observed:
        return {
            'synced': False,
            'mismatch': False,
            'directoryId': sanitize_directory_id(directory_id),
            'claimPricing': claim,
            'observedPricing': observed,
            'note': None,
            'ok': True,
        }
    if client is None:
        note = admin_sync_note('pricing', ok=False, status_code=None)
        return {
            'synced': False,
            'mismatch': True,
            'directoryId': sanitize_directory_id(directory_id),
            'claimPricing': claim,
            'observedPricing': observed,
            'note': note,
            'ok': False,
            'statusCode': None,
        }
    result = client.update_directory(directory_id, pricing=observed)
    return {
        'synced': bool(result.get('ok')),
        'mismatch': True,
        'directoryId': sanitize_directory_id(directory_id),
        'claimPricing': claim,
        'observedPricing': observed,
        'note': result.get('note'),
        'ok': bool(result.get('ok')),
        'statusCode': result.get('statusCode'),
        'response': result,
    }


def maybe_reject_after_unavailable(
    client: DirectoryAdminClient | None,
    *,
    directory_id: str,
    shipmore_consecutive_count: int | None = None,
) -> dict[str, Any]:
    """On 3rd consecutive unavailable, PATCH status to rejected; still complete item."""
    streak = record_unavailable_outcome(
        directory_id,
        shipmore_consecutive_count=shipmore_consecutive_count,
    )
    if not streak['shouldRejectDirectory']:
        return {
            **streak,
            'rejected': False,
            'note': None,
            'ok': True,
        }
    if client is None:
        note = admin_sync_note('status', ok=False, status_code=None)
        return {
            **streak,
            'rejected': False,
            'note': note,
            'ok': False,
            'statusCode': None,
        }
    # Prefer status-only endpoint; keep reason short if full update is used later.
    result = client.update_directory_status(directory_id, 'rejected')
    return {
        **streak,
        'rejected': bool(result.get('ok')),
        'note': result.get('note'),
        'ok': bool(result.get('ok')),
        'statusCode': result.get('statusCode'),
        'response': result,
    }


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        '--base-url',
        default=env('BACKLINK_APP_URL'),
        help='Shipmore base URL; defaults to BACKLINK_APP_URL',
    )
    common.add_argument(
        '--api-key',
        default=None,
        help=argparse.SUPPRESS,
    )
    common.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f'HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})',
    )

    parser = argparse.ArgumentParser(
        description=(
            'Shipmore Directory Admin API client '
            f'({SHIPMORE_API_KEY_ENV} + x-api-key; never logs the key)'
        ),
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    update = subparsers.add_parser(
        'admin-update-directory',
        parents=[common],
        help='PATCH /api/admin/directories (pricing/status/etc.)',
    )
    update.add_argument('--directory-id', required=True)
    update.add_argument('--pricing', choices=DIRECTORY_PRICING)
    update.add_argument('--status', choices=DIRECTORY_STATUSES)
    update.add_argument('--rejected-reason')
    update.add_argument(
        '--dofollow',
        choices=['true', 'false'],
        help='Optional dofollow flag',
    )

    status = subparsers.add_parser(
        'admin-update-directory-status',
        parents=[common],
        help='PATCH /api/admin/directories/status',
    )
    status.add_argument('--directory-id', required=True)
    status.add_argument('--status', required=True, choices=DIRECTORY_STATUSES)

    sync_pricing = subparsers.add_parser(
        'sync-observed-pricing',
        parents=[common],
        help='Sync Directory Admin pricing when observation disagrees with claim',
    )
    sync_pricing.add_argument('--directory-id', required=True)
    sync_pricing.add_argument(
        '--claim-pricing',
        required=True,
        choices=DIRECTORY_PRICING,
    )
    sync_pricing.add_argument(
        '--observed-pricing',
        required=True,
        help=(
            'Observed enum/alias, or comma-separated paths when the page offers '
            'more than one. Classify each path first: Free/$0 that still requires '
            'badge/reciprocal/backlink is backlink, never free. Then resolve with '
            'priority free > backlink > paid'
        ),
    )

    note_unavailable = subparsers.add_parser(
        'note-unavailable',
        parents=[common],
        help=(
            'Record consecutive unavailable for a directory; '
            'reject via Admin API on the 3rd consecutive'
        ),
    )
    note_unavailable.add_argument('--directory-id', required=True)
    note_unavailable.add_argument(
        '--shipmore-consecutive-count',
        type=int,
        help=(
            'Prefer Shipmore-backed consecutive unavailable count for this '
            'directory when history is available (includes this attempt)'
        ),
    )
    note_unavailable.add_argument(
        '--skip-admin-reject',
        action='store_true',
        help='Only update local/Shipmore streak state; do not call Admin API',
    )

    reset = subparsers.add_parser(
        'note-reachable-attempt',
        parents=[common],
        help='Reset consecutive unavailable counter after a non-unavailable attempt',
    )
    reset.add_argument('--directory-id', required=True)

    return parser


def _client_from_args(args: argparse.Namespace) -> DirectoryAdminClient:
    base_url = require(
        args.base_url,
        'Missing Shipmore base URL. Set BACKLINK_APP_URL or pass --base-url.',
    )
    api_key = require(
        resolve_admin_api_key(getattr(args, 'api_key', None)),
        f'Missing ShipMore API key. Set {SHIPMORE_API_KEY_ENV}.',
    )
    return DirectoryAdminClient(
        base_url=base_url,
        api_key=api_key,
        timeout=args.timeout,
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == 'admin-update-directory':
            client = _client_from_args(args)
            dofollow = None
            if args.dofollow is not None:
                dofollow = args.dofollow == 'true'
            result = client.update_directory(
                args.directory_id,
                pricing=args.pricing,
                status=args.status,
                rejected_reason=args.rejected_reason,
                dofollow=dofollow,
            )
        elif args.command == 'admin-update-directory-status':
            client = _client_from_args(args)
            result = client.update_directory_status(args.directory_id, args.status)
        elif args.command == 'sync-observed-pricing':
            api_key = resolve_admin_api_key(getattr(args, 'api_key', None))
            client = None
            if api_key and args.base_url:
                client = DirectoryAdminClient(
                    base_url=require(args.base_url, 'Missing Shipmore base URL.'),
                    api_key=api_key,
                    timeout=args.timeout,
                )
            elif api_key:
                client = _client_from_args(args)
            result = sync_pricing_if_mismatch(
                client,
                directory_id=args.directory_id,
                claim_pricing=args.claim_pricing,
                observed_pricing=args.observed_pricing,
            )
        elif args.command == 'note-unavailable':
            if args.skip_admin_reject:
                result = record_unavailable_outcome(
                    args.directory_id,
                    shipmore_consecutive_count=args.shipmore_consecutive_count,
                )
            else:
                api_key = resolve_admin_api_key(getattr(args, 'api_key', None))
                client = None
                if api_key and args.base_url:
                    try:
                        client = DirectoryAdminClient(
                            base_url=require(
                                args.base_url, 'Missing Shipmore base URL.'
                            ),
                            api_key=api_key,
                            timeout=args.timeout,
                        )
                    except DirectoryAdminError:
                        client = None
                result = maybe_reject_after_unavailable(
                    client,
                    directory_id=args.directory_id,
                    shipmore_consecutive_count=args.shipmore_consecutive_count,
                )
        elif args.command == 'note-reachable-attempt':
            result = reset_unavailable_streak(args.directory_id)
        else:
            raise DirectoryAdminError(f'Unknown command: {args.command}')

        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        # Direct admin-* commands fail on non-2xx. sync/note helpers always
        # exit 0 after producing a non-secret note so workers can still complete.
        soft_commands = {
            'sync-observed-pricing',
            'note-unavailable',
            'note-reachable-attempt',
        }
        if (
            args.command not in soft_commands
            and isinstance(result, dict)
            and result.get('ok') is False
        ):
            return 1
        return 0
    except DirectoryAdminError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
