#!/usr/bin/env python3
"""Dependency-free client for the Shipmore backlink agent queue API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_LEASE_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 30


class ShipmoreClientError(RuntimeError):
    pass


def env(name: str, fallback: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return fallback
    return value.strip()


def require(value: str | None, message: str) -> str:
    if value is None or not value.strip():
        raise ShipmoreClientError(message)
    return value.strip()


def compact_optional(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


class ShipmoreQueueClient:
    def __init__(self, base_url: str, token: str, worker_id: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.worker_id = worker_id
        self.timeout = timeout

    @property
    def queue_url(self) -> str:
        return f'{self.base_url}/api/backlinks/agent/queue'

    def post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        request = Request(
            self.queue_url,
            data=body,
            method='POST',
            headers={
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'shipmore-backlink-skill/1.0',
            },
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode('utf-8')
        except HTTPError as exc:
            raw = exc.read().decode('utf-8', errors='replace')
            try:
                error_body = json.loads(raw)
            except json.JSONDecodeError:
                error_body = {'raw': raw}
            raise ShipmoreClientError(
                f'HTTP {exc.code}: {json.dumps(error_body, ensure_ascii=False)}'
            ) from exc
        except URLError as exc:
            raise ShipmoreClientError(f'Network error: {exc.reason}') from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ShipmoreClientError('Shipmore returned non-JSON data') from exc

        if not isinstance(parsed, dict):
            raise ShipmoreClientError('Shipmore returned an unexpected JSON payload')
        return parsed

    def claim(self, run_id: str, lease_seconds: int) -> dict[str, Any]:
        return self.post(
            {
                'operation': 'claim',
                'runId': run_id,
                'workerId': self.worker_id,
                'leaseSeconds': lease_seconds,
            }
        )

    def heartbeat(self, run_item_id: str, lease_seconds: int) -> dict[str, Any]:
        return self.post(
            {
                'operation': 'heartbeat',
                'runItemId': run_item_id,
                'workerId': self.worker_id,
                'leaseSeconds': lease_seconds,
            }
        )

    def recover(self, run_id: str | None = None) -> dict[str, Any]:
        return self.post(compact_optional({'operation': 'recover', 'runId': run_id}))

    def complete(self, args: argparse.Namespace) -> dict[str, Any]:
        payload = compact_optional(
            {
                'operation': 'complete',
                'eventId': args.event_id,
                'runItemId': args.run_item_id,
                'workerId': self.worker_id,
                'status': args.status,
                'submissionStatus': args.submission_status,
                'verificationStatus': args.verification_status,
                'lastError': args.last_error,
                'exactResult': args.exact_result,
                'evidenceReference': args.evidence_reference,
                'publicListingUrl': args.public_listing_url,
                'backendCheckedAt': args.backend_checked_at,
                'mailboxCheckedAt': args.mailbox_checked_at,
                'publicPageCheckedAt': args.public_page_checked_at,
                'followUpAt': args.follow_up_at,
                'followUpNote': args.follow_up_note,
            }
        )
        return self.post(payload)


def add_common_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--base-url',
        default=env('BACKLINK_APP_URL'),
        help='Shipmore base URL; defaults to BACKLINK_APP_URL',
    )
    parser.add_argument(
        '--token',
        default=env('BACKLINK_AGENT_TOKEN'),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        '--worker-id',
        default=env('BACKLINK_WORKER_ID'),
        help='Stable worker alias; defaults to BACKLINK_WORKER_ID',
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f'HTTP timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})',
    )


def add_lease_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--lease-seconds',
        type=int,
        default=DEFAULT_LEASE_SECONDS,
        choices=range(30, 3601),
        metavar='30..3600',
        help=f'Lease duration in seconds (default: {DEFAULT_LEASE_SECONDS})',
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Shipmore backlink submission Queue API client'
    )
    add_common_connection_args(parser)
    subparsers = parser.add_subparsers(dest='command', required=True)

    claim = subparsers.add_parser('claim', help='Claim or reuse one Run Item lease')
    claim.add_argument('--run-id', required=True)
    add_lease_arg(claim)

    heartbeat = subparsers.add_parser('heartbeat', help='Heartbeat one leased Run Item')
    heartbeat.add_argument('--run-item-id', required=True)
    add_lease_arg(heartbeat)

    recover = subparsers.add_parser('recover', help='Recover expired Run Item leases')
    recover.add_argument('--run-id')

    complete = subparsers.add_parser('complete', help='Complete one leased Run Item')
    complete.add_argument('--run-item-id', required=True)
    complete.add_argument('--event-id', required=True)
    complete.add_argument(
        '--status',
        required=True,
        choices=['completed', 'blocked', 'failed', 'skipped'],
    )
    complete.add_argument('--submission-status', required=True)
    complete.add_argument('--verification-status')
    complete.add_argument('--last-error')
    complete.add_argument('--exact-result')
    complete.add_argument('--evidence-reference')
    complete.add_argument('--public-listing-url')
    complete.add_argument('--backend-checked-at')
    complete.add_argument('--mailbox-checked-at')
    complete.add_argument('--public-page-checked-at')
    complete.add_argument('--follow-up-at')
    complete.add_argument('--follow-up-note')

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        base_url = require(
            args.base_url,
            'Missing Shipmore base URL. Set BACKLINK_APP_URL or pass --base-url.',
        )
        token = require(
            args.token,
            'Missing agent token. Set BACKLINK_AGENT_TOKEN.',
        )
        worker_id = require(
            args.worker_id,
            'Missing stable worker ID. Set BACKLINK_WORKER_ID or pass --worker-id.',
        )

        client = ShipmoreQueueClient(
            base_url=base_url,
            token=token,
            worker_id=worker_id,
            timeout=args.timeout,
        )

        if args.command == 'claim':
            result = client.claim(args.run_id, args.lease_seconds)
        elif args.command == 'heartbeat':
            result = client.heartbeat(args.run_item_id, args.lease_seconds)
        elif args.command == 'recover':
            result = client.recover(args.run_id)
        elif args.command == 'complete':
            result = client.complete(args)
        else:
            raise ShipmoreClientError(f'Unknown command: {args.command}')

        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except ShipmoreClientError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
