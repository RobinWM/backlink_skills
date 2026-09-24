#!/usr/bin/env python3
"""Dependency-free client for the Shipmore backlink agent queue API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


DEFAULT_LEASE_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 30
BACKLINK_POLL_ATTEMPTS = 6
BACKLINK_POLL_INTERVAL_SECONDS = 20

SUBMISSION_STATUSES = [
    'not_attempted',
    'form_in_progress',
    'draft_saved',
    'submitted',
    'submission_outcome_unknown',
    'awaiting_approval',
    'awaiting_email_verification',
    'email_sent_awaiting_reply',
    'email_send_outcome_unknown',
    'published',
    'blocked_manual_verification',
    'blocked_missing_verified_data',
    'blocked_account_or_email_policy',
    'unavailable',
    'paid_only',
    'ineligible',
    'duplicate_no_action',
    'terminated_by_user',
    'rejected',
]

VERIFICATION_STATUSES = [
    'not_checked',
    'automatic_verification_passed',
    'awaiting_manual_verification',
    'manual_verification_completed',
    'verification_unavailable_before_form',
    'verification_expired_reset',
    'no_verification_presented',
    'deferred_by_user',
]

ACTION_CHANNELS = ['web_form', 'official_contact_email']
CONTENT_SURFACES = [
    'not_applicable',
    'directory_listing',
    'product_profile',
    'claim_listing',
    'short_note_no_action',
    'long_post_no_action',
    'unknown_no_action',
    'official_contact_email',
]


class ShipmoreClientError(RuntimeError):
    pass


class AnchorHrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != 'a':
            return
        for name, value in attrs:
            if name.lower() == 'href' and value:
                self.hrefs.append(value.strip())
                return


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


def normalize_http_url(url: str) -> str:
    trimmed = url.strip()
    if not trimmed:
        raise ShipmoreClientError('URL is empty')
    if trimmed.startswith('//'):
        trimmed = f'https:{trimmed}'
    elif not trimmed.lower().startswith(('http://', 'https://')):
        trimmed = f'https://{trimmed}'

    parsed = urlsplit(trimmed)
    if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname:
        raise ShipmoreClientError(f'Invalid HTTP URL: {url}')
    return trimmed


def normalized_link_identity(url: str) -> tuple[str, str]:
    parsed = urlsplit(normalize_http_url(url))
    hostname = (parsed.hostname or '').lower().rstrip('.')
    if hostname.startswith('www.'):
        hostname = hostname[4:]
    if not hostname:
        raise ShipmoreClientError(f'URL has no hostname: {url}')

    path = parsed.path or '/'
    if path != '/':
        path = path.rstrip('/') or '/'
    return hostname, path


def find_matching_outbound_link(
    html: str,
    page_url: str,
    directory_url: str,
) -> str | None:
    target = normalized_link_identity(directory_url)
    parser = AnchorHrefParser()
    parser.feed(html)
    for href in parser.hrefs:
        absolute_url = urljoin(page_url, href)
        try:
            candidate = normalized_link_identity(absolute_url)
        except ShipmoreClientError:
            continue
        if candidate == target:
            return absolute_url
    return None


def fetch_homepage_html(url: str, timeout: int) -> tuple[str, str]:
    normalized_url = normalize_http_url(url)
    request = Request(
        normalized_url,
        method='GET',
        headers={
            'Accept': 'text/html,application/xhtml+xml',
            'User-Agent': 'shipmore-backlink-skill/1.0',
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            html = response.read().decode(charset, errors='replace')
            final_url = response.geturl()
    except HTTPError as exc:
        raise ShipmoreClientError(
            f'Product homepage returned HTTP {exc.code}: {normalized_url}'
        ) from exc
    except URLError as exc:
        raise ShipmoreClientError(
            f'Product homepage network error: {exc.reason}'
        ) from exc
    return html, final_url


class ShipmoreQueueClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        worker_id: str | None = None,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.worker_id = worker_id
        self.timeout = timeout

    @property
    def queue_url(self) -> str:
        return f'{self.base_url}/api/backlinks/agent/queue'

    @property
    def outbound_links_url(self) -> str:
        return f'{self.base_url}/api/outbound-links'

    def require_worker_id(self) -> str:
        return require(
            self.worker_id,
            'Missing stable worker ID. Set BACKLINK_WORKER_ID or pass --worker-id.',
        )

    def post(
        self,
        payload: dict[str, Any],
        url: str | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        request = Request(
            url or self.queue_url,
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
                'workerId': self.require_worker_id(),
                'leaseSeconds': lease_seconds,
            }
        )

    def heartbeat(self, run_item_id: str, lease_seconds: int) -> dict[str, Any]:
        return self.post(
            {
                'operation': 'heartbeat',
                'runItemId': run_item_id,
                'workerId': self.require_worker_id(),
                'leaseSeconds': lease_seconds,
            }
        )

    def register_outbound_link(self, run_item_id: str) -> dict[str, Any]:
        return self.post(
            {
                'runItemId': run_item_id,
                'workerId': self.require_worker_id(),
            },
            url=self.outbound_links_url,
        )

    def add_outbound_link(
        self,
        run_item_id: str,
        product_url: str,
        directory_url: str,
        lease_seconds: int,
        *,
        attempts: int = BACKLINK_POLL_ATTEMPTS,
        interval_seconds: int = BACKLINK_POLL_INTERVAL_SECONDS,
        fetcher=fetch_homepage_html,
        sleeper=time.sleep,
    ) -> dict[str, Any]:
        if not 1 <= attempts <= BACKLINK_POLL_ATTEMPTS:
            raise ShipmoreClientError(
                f'Backlink verification attempts must be between 1 and '
                f'{BACKLINK_POLL_ATTEMPTS}'
            )
        product_url = normalize_http_url(product_url)
        directory_url = normalize_http_url(directory_url)

        heartbeat = self.heartbeat(run_item_id, lease_seconds)
        if heartbeat.get('success') is False:
            raise ShipmoreClientError('Heartbeat failed before backlink registration')

        registration = self.register_outbound_link(run_item_id)
        if registration.get('success') is False:
            raise ShipmoreClientError('Outbound-link registration was rejected')

        registration_data = registration.get('data')
        registered_directory_url = (
            registration_data.get('directoryUrl')
            if isinstance(registration_data, dict)
            else None
        )
        if not isinstance(registered_directory_url, str):
            raise ShipmoreClientError(
                'Outbound-link registration response is missing directoryUrl'
            )
        registered_directory_url = normalize_http_url(registered_directory_url)
        if normalized_link_identity(registered_directory_url) != normalized_link_identity(
            directory_url
        ):
            raise ShipmoreClientError(
                'Outbound-link registration directory does not match the claimed task'
            )
        directory_url = registered_directory_url

        last_fetch_error: str | None = None
        for attempt in range(1, attempts + 1):
            heartbeat = self.heartbeat(run_item_id, lease_seconds)
            if heartbeat.get('success') is False:
                raise ShipmoreClientError(
                    f'Heartbeat failed before backlink verification attempt {attempt}'
                )

            final_product_url = product_url
            try:
                html, final_product_url = fetcher(product_url, self.timeout)
                last_fetch_error = None
                matched_url = find_matching_outbound_link(
                    html,
                    final_product_url,
                    directory_url,
                )
            except ShipmoreClientError as exc:
                last_fetch_error = str(exc)
                matched_url = None
            if matched_url:
                return {
                    'success': True,
                    'reason': 'backlink_verified',
                    'runItemId': run_item_id,
                    'workerId': self.require_worker_id(),
                    'attempt': attempt,
                    'productUrl': final_product_url,
                    'directoryUrl': directory_url,
                    'matchedUrl': matched_url,
                    'registration': registration,
                }

            if attempt < attempts:
                sleeper(interval_seconds)

        detail = f'; last fetch error: {last_fetch_error}' if last_fetch_error else ''
        raise ShipmoreClientError(
            'backlink verification timeout: directory link was not found on the '
            f'product homepage after {attempts} attempts{detail}'
        )

    def recover(self, run_id: str | None = None) -> dict[str, Any]:
        return self.post(compact_optional({'operation': 'recover', 'runId': run_id}))

    def complete(self, args: argparse.Namespace) -> dict[str, Any]:
        if args.status == 'failed' and not (args.last_error or '').strip():
            raise ShipmoreClientError('--last-error is required when --status failed')
        if args.submission_status == 'published' and not (
            args.public_listing_url or ''
        ).strip():
            raise ShipmoreClientError(
                '--public-listing-url is required when --submission-status published'
            )

        retry_diagnostic = None
        retry_diagnostic_json = getattr(args, 'retry_diagnostic_json', None)
        if retry_diagnostic_json:
            try:
                retry_diagnostic = json.loads(retry_diagnostic_json)
            except json.JSONDecodeError as exc:
                raise ShipmoreClientError(
                    '--retry-diagnostic-json must be valid JSON'
                ) from exc
            if not isinstance(retry_diagnostic, dict):
                raise ShipmoreClientError(
                    '--retry-diagnostic-json must contain a JSON object'
                )

        payload = compact_optional(
            {
                'operation': 'complete',
                'eventId': args.event_id,
                'runItemId': args.run_item_id,
                'workerId': self.require_worker_id(),
                'status': args.status,
                'submissionStatus': args.submission_status,
                'actionChannel': getattr(args, 'action_channel', None),
                'contentSurface': getattr(args, 'content_surface', None),
                'contentSurfaceEvidence': getattr(args, 'content_surface_evidence', None),
                'recipientContactAlias': getattr(args, 'recipient_contact_alias', None),
                'contactSourceEvidence': getattr(args, 'contact_source_evidence', None),
                'mailboxPreSendCheck': getattr(args, 'mailbox_pre_send_check', None),
                'mailboxPreSendEvidence': getattr(args, 'mailbox_pre_send_evidence', None),
                'emailSendAttempts': getattr(args, 'email_send_attempts', None),
                'gmailSendReceipt': getattr(args, 'gmail_send_receipt', None),
                'retryDiagnostic': retry_diagnostic,
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

    add_outbound_link = subparsers.add_parser(
        'add-outbound-link',
        help='Register and verify a mandatory directory backlink',
    )
    add_outbound_link.add_argument('--run-item-id', required=True)
    add_outbound_link.add_argument('--product-url', required=True)
    add_outbound_link.add_argument('--directory-url', required=True)
    add_lease_arg(add_outbound_link)

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
    complete.add_argument(
        '--submission-status', required=True, choices=SUBMISSION_STATUSES
    )
    complete.add_argument('--action-channel', choices=ACTION_CHANNELS)
    complete.add_argument('--content-surface', choices=CONTENT_SURFACES)
    complete.add_argument('--content-surface-evidence')
    complete.add_argument('--recipient-contact-alias')
    complete.add_argument('--contact-source-evidence')
    complete.add_argument('--mailbox-pre-send-check')
    complete.add_argument('--mailbox-pre-send-evidence')
    complete.add_argument('--email-send-attempts', type=int, choices=[0, 1])
    complete.add_argument('--gmail-send-receipt')
    complete.add_argument(
        '--retry-diagnostic-json',
        help='JSON object describing one controlled retry diagnosis',
    )
    complete.add_argument('--verification-status', choices=VERIFICATION_STATUSES)
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

        client = ShipmoreQueueClient(
            base_url=base_url,
            token=token,
            worker_id=args.worker_id,
            timeout=args.timeout,
        )

        if args.command == 'claim':
            result = client.claim(args.run_id, args.lease_seconds)
        elif args.command == 'heartbeat':
            result = client.heartbeat(args.run_item_id, args.lease_seconds)
        elif args.command == 'add-outbound-link':
            result = client.add_outbound_link(
                args.run_item_id,
                args.product_url,
                args.directory_url,
                args.lease_seconds,
            )
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
