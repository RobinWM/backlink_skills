#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from shipmore_queue_client import (  # noqa: E402
    ShipmoreClientError,
    ShipmoreQueueClient,
    apply_debug_history_view,
    build_parser,
    find_matching_outbound_link,
)


class RecordingClient(ShipmoreQueueClient):
    def __init__(
        self,
        worker_id: str | None = 'worker-01',
        registered_directory_url: str = 'https://directory.example',
    ):
        super().__init__(
            base_url='https://shipmore.example',
            token='test-token',
            worker_id=worker_id,
        )
        self.last_payload = None
        self.last_url = None
        self.calls = []
        self.registered_directory_url = registered_directory_url

    def post(self, payload, url=None):
        self.last_payload = payload
        self.last_url = url or self.queue_url
        self.calls.append((self.last_url, payload))
        if self.last_url == self.outbound_links_url:
            return {
                'success': True,
                'data': {
                    'directoryUrl': self.registered_directory_url,
                    'linkedHref': self.registered_directory_url,
                },
            }
        return payload


class ShipmoreQueueClientTests(unittest.TestCase):
    def test_claim_payload(self):
        client = RecordingClient()
        result = client.claim('run-1', 300)
        self.assertEqual(
            result,
            {
                'operation': 'claim',
                'runId': 'run-1',
                'workerId': 'worker-01',
                'leaseSeconds': 300,
            },
        )

    def test_debug_history_view_masks_business_history_only(self):
        original = {
            'success': True,
            'reason': 'reused',
            'data': {
                'id': 'item-1',
                'status': 'running',
                'claimedBy': 'worker-01',
                'leaseExpiresAt': '2026-09-29T09:00:00Z',
                'productDirectoryId': 'pd-1',
                'submissionStatus': 'blocked_manual_verification',
                'verificationStatus': 'awaiting_manual_verification',
                'route': 'submit',
                'accountAlias': 'old-account',
                'submittedAt': '2026-09-28T10:00:00Z',
                'exactResult': 'old result',
                'evidenceReference': 'ev-old',
                'publicListingUrl': 'https://directory.example/item',
                'backendCheckedAt': '2026-09-28T11:00:00Z',
                'mailboxCheckedAt': '2026-09-28T11:05:00Z',
                'publicPageCheckedAt': '2026-09-28T11:10:00Z',
                'lastCheckedAt': '2026-09-28T11:15:00Z',
                'followUpAt': '2026-09-30T10:00:00Z',
                'followUpNote': 'old follow-up',
                'actionChannel': 'web_form',
                'contentSurface': 'directory_listing',
                'contentSurfaceEvidence': 'old content evidence',
                'recipientContactAlias': 'old alias',
                'contactSourceEvidence': 'old contact evidence',
                'mailboxPreSendCheck': 'old mailbox check',
                'mailboxPreSendEvidence': 'old mailbox evidence',
                'emailSendAttempts': 1,
                'gmailSendReceipt': 'old receipt',
                'productName': 'Current Product',
                'directoryName': 'Current Directory',
            },
        }

        with patch.dict(os.environ, {'SHIPMORE_DEBUG_IGNORE_HISTORY': '1'}):
            result = apply_debug_history_view(original)

        self.assertTrue(result['debugHistoryIgnored'])
        self.assertEqual(result['reason'], 'reused')
        self.assertEqual(result['data']['id'], 'item-1')
        self.assertEqual(result['data']['status'], 'running')
        self.assertEqual(result['data']['claimedBy'], 'worker-01')
        self.assertEqual(
            result['data']['leaseExpiresAt'],
            '2026-09-29T09:00:00Z',
        )
        self.assertEqual(result['data']['submissionStatus'], 'not_attempted')
        self.assertEqual(result['data']['verificationStatus'], 'not_checked')
        self.assertIsNone(result['data']['exactResult'])
        self.assertIsNone(result['data']['publicListingUrl'])
        self.assertIsNone(result['data']['route'])
        self.assertIsNone(result['data']['accountAlias'])
        self.assertEqual(result['data']['emailSendAttempts'], 0)
        self.assertEqual(result['data']['productName'], 'Current Product')
        self.assertEqual(result['data']['directoryName'], 'Current Directory')

    def test_claim_applies_debug_history_view_when_enabled(self):
        client = RecordingClient()
        client.post = lambda payload, url=None: {
            'success': True,
            'reason': 'claimed',
            'data': {
                'id': 'item-debug',
                'status': 'claimed',
                'claimedBy': 'worker-01',
                'leaseExpiresAt': '2026-09-29T09:00:00Z',
                'productDirectoryId': 'pd-debug',
                'submissionStatus': 'published',
                'verificationStatus': 'automatic_verification_passed',
                'exactResult': 'old published result',
                'publicListingUrl': 'https://directory.example/published',
                'productName': 'Debug Product',
            },
        }

        with patch.dict(os.environ, {'SHIPMORE_DEBUG_IGNORE_HISTORY': '1'}):
            result = client.claim('run-debug', 300)

        self.assertTrue(result['debugHistoryIgnored'])
        self.assertEqual(result['reason'], 'claimed')
        self.assertEqual(result['data']['status'], 'claimed')
        self.assertEqual(result['data']['submissionStatus'], 'not_attempted')
        self.assertEqual(result['data']['verificationStatus'], 'not_checked')
        self.assertIsNone(result['data']['exactResult'])
        self.assertIsNone(result['data']['publicListingUrl'])
        self.assertEqual(result['data']['productName'], 'Debug Product')

    def test_debug_history_view_is_off_by_default(self):
        original = {
            'success': True,
            'reason': 'claimed',
            'data': {
                'productDirectoryId': 'pd-1',
                'submissionStatus': 'published',
                'verificationStatus': 'automatic_verification_passed',
            },
        }
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('SHIPMORE_DEBUG_IGNORE_HISTORY', None)
            result = apply_debug_history_view(original)
        self.assertIs(result, original)
        self.assertEqual(result['data']['submissionStatus'], 'published')

    def test_heartbeat_payload(self):
        client = RecordingClient()
        result = client.heartbeat('item-1', 600)
        self.assertEqual(
            result,
            {
                'operation': 'heartbeat',
                'runItemId': 'item-1',
                'workerId': 'worker-01',
                'leaseSeconds': 600,
            },
        )

    def test_register_outbound_link_posts_exact_body_to_endpoint(self):
        client = RecordingClient()

        result = client.register_outbound_link('item-1')

        self.assertEqual(
            result,
            {
                'success': True,
                'data': {
                    'directoryUrl': 'https://directory.example',
                    'linkedHref': 'https://directory.example',
                },
            },
        )
        self.assertEqual(
            client.last_url,
            'https://shipmore.example/api/outbound-links',
        )

    def test_register_outbound_link_requires_worker_id(self):
        client = RecordingClient(worker_id=None)

        with self.assertRaises(ShipmoreClientError):
            client.register_outbound_link('item-1')

    def test_add_outbound_link_heartbeats_registers_and_verifies(self):
        client = RecordingClient(
            registered_directory_url='https://directory.example/submit'
        )
        fetches = []

        def fetcher(url, timeout):
            fetches.append((url, timeout))
            return (
                '<footer><a href="http://www.directory.example/submit/">Badge</a></footer>',
                'https://product.example/',
            )

        result = client.add_outbound_link(
            'item-1',
            'https://product.example',
            'https://directory.example/submit',
            300,
            attempts=1,
            interval_seconds=0,
            fetcher=fetcher,
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['reason'], 'backlink_verified')
        self.assertEqual(result['attempt'], 1)
        self.assertEqual(
            result['matchedUrl'],
            'http://www.directory.example/submit/',
        )
        self.assertEqual(fetches, [('https://product.example', 30)])
        self.assertEqual(len(client.calls), 3)
        self.assertEqual(client.calls[0][1]['operation'], 'heartbeat')
        self.assertEqual(
            client.calls[1],
            (
                'https://shipmore.example/api/outbound-links',
                {'runItemId': 'item-1', 'workerId': 'worker-01'},
            ),
        )
        self.assertEqual(client.calls[2][1]['operation'], 'heartbeat')

    def test_add_outbound_link_rejects_registration_directory_mismatch(self):
        client = RecordingClient()

        with self.assertRaisesRegex(
            ShipmoreClientError,
            'registration directory does not match',
        ):
            client.add_outbound_link(
                'item-1',
                'product.example',
                'other-directory.example',
                300,
                attempts=1,
                interval_seconds=0,
                fetcher=lambda url, timeout: ('', url),
            )

    def test_add_outbound_link_times_out_without_matching_anchor(self):
        client = RecordingClient()

        with self.assertRaisesRegex(
            ShipmoreClientError,
            'backlink verification timeout',
        ):
            client.add_outbound_link(
                'item-1',
                'https://product.example',
                'https://directory.example',
                300,
                attempts=2,
                interval_seconds=0,
                fetcher=lambda url, timeout: (
                    '<a href="https://notdirectory.example">Wrong</a>',
                    url,
                ),
                sleeper=lambda seconds: None,
            )

    def test_add_outbound_link_accepts_bare_product_and_directory_domains(self):
        client = RecordingClient()
        fetched_urls = []

        def fetcher(url, timeout):
            fetched_urls.append(url)
            return '<a href="https://directory.example">Directory</a>', url

        result = client.add_outbound_link(
            'item-1',
            'product.example',
            'directory.example',
            300,
            attempts=1,
            interval_seconds=0,
            fetcher=fetcher,
        )

        self.assertTrue(result['success'])
        self.assertEqual(fetched_urls, ['https://product.example'])
        self.assertEqual(result['directoryUrl'], 'https://directory.example')

    def test_add_outbound_link_retries_transient_homepage_fetch_errors(self):
        client = RecordingClient()
        fetch_attempts = []

        def fetcher(url, timeout):
            fetch_attempts.append(url)
            if len(fetch_attempts) == 1:
                raise ShipmoreClientError('temporary network failure')
            return '<a href="https://directory.example">Directory</a>', url

        result = client.add_outbound_link(
            'item-1',
            'product.example',
            'directory.example',
            300,
            attempts=2,
            interval_seconds=0,
            fetcher=fetcher,
            sleeper=lambda seconds: None,
        )

        self.assertEqual(result['attempt'], 2)
        self.assertEqual(len(fetch_attempts), 2)

    def test_exact_anchor_matching_avoids_substring_false_positives(self):
        html = (
            '<a href="https://directory.example.evil.test/">host suffix</a>'
            '<a href="https://directory.example/other">wrong path</a>'
        )

        self.assertIsNone(
            find_matching_outbound_link(
                html,
                'https://product.example/',
                'http://www.directory.example/',
            )
        )

    def test_add_outbound_link_cli_arguments(self):
        args = build_parser().parse_args(
            [
                'add-outbound-link',
                '--run-item-id',
                'item-1',
                '--product-url',
                'https://product.example',
                '--directory-url',
                'https://directory.example',
            ]
        )

        self.assertEqual(args.command, 'add-outbound-link')
        self.assertEqual(args.run_item_id, 'item-1')
        self.assertEqual(args.product_url, 'https://product.example')
        self.assertEqual(args.directory_url, 'https://directory.example')
        self.assertEqual(args.lease_seconds, 300)

    def test_recover_does_not_require_worker_id(self):
        client = RecordingClient(worker_id=None)
        self.assertEqual(client.recover(), {'operation': 'recover'})
        self.assertEqual(
            client.recover('run-1'),
            {'operation': 'recover', 'runId': 'run-1'},
        )

    def test_complete_payload(self):
        client = RecordingClient()
        args = argparse.Namespace(
            event_id='evt-1',
            run_item_id='item-1',
            status='completed',
            submission_status='awaiting_approval',
            verification_status='no_verification_presented',
            last_error=None,
            exact_result='Queued for review',
            evidence_reference='ev-1',
            public_listing_url=None,
            backend_checked_at=None,
            mailbox_checked_at=None,
            public_page_checked_at=None,
            follow_up_at=None,
            follow_up_note=None,
        )
        result = client.complete(args)
        self.assertEqual(result['operation'], 'complete')
        self.assertEqual(result['eventId'], 'evt-1')
        self.assertEqual(result['runItemId'], 'item-1')
        self.assertEqual(result['workerId'], 'worker-01')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['submissionStatus'], 'awaiting_approval')
        self.assertEqual(
            result['verificationStatus'], 'no_verification_presented'
        )
        self.assertEqual(result['exactResult'], 'Queued for review')
        self.assertEqual(result['evidenceReference'], 'ev-1')
        self.assertNotIn('lastError', result)
        self.assertNotIn('publicListingUrl', result)

    def test_failed_complete_requires_last_error(self):
        client = RecordingClient()
        args = argparse.Namespace(
            event_id='evt-1',
            run_item_id='item-1',
            status='failed',
            submission_status='not_attempted',
            verification_status=None,
            last_error=None,
            exact_result=None,
            evidence_reference=None,
            public_listing_url=None,
            backend_checked_at=None,
            mailbox_checked_at=None,
            public_page_checked_at=None,
            follow_up_at=None,
            follow_up_note=None,
        )
        with self.assertRaises(ShipmoreClientError):
            client.complete(args)

    def test_published_complete_requires_public_url(self):
        client = RecordingClient()
        args = argparse.Namespace(
            event_id='evt-1',
            run_item_id='item-1',
            status='completed',
            submission_status='published',
            verification_status=None,
            last_error=None,
            exact_result=None,
            evidence_reference=None,
            public_listing_url=None,
            backend_checked_at=None,
            mailbox_checked_at=None,
            public_page_checked_at=None,
            follow_up_at=None,
            follow_up_note=None,
        )
        with self.assertRaises(ShipmoreClientError):
            client.complete(args)

    def test_complete_payload_accepts_retry_diagnostic_json(self):
        client = RecordingClient()
        args = argparse.Namespace(
            event_id='evt-2',
            run_item_id='item-2',
            status='failed',
            submission_status='form_in_progress',
            verification_status=None,
            last_error='agent-browser timeout after read-only check',
            exact_result='Retry diagnosis recorded',
            evidence_reference='ev-2',
            public_listing_url=None,
            backend_checked_at=None,
            mailbox_checked_at=None,
            public_page_checked_at=None,
            follow_up_at=None,
            follow_up_note=None,
            retry_diagnostic_json='{"exactError":"timeout","failedAction":"read","targetUrl":"https://example.test","pageState":"form","hypothesisA":"slow load","hypothesisB":"stale tab","minimalReadOnlyCheck":"read page","nextActionDifference":"fresh tab"}',
        )
        result = client.complete(args)
        self.assertEqual(result['retryDiagnostic']['nextActionDifference'], 'fresh tab')

    def test_invalid_retry_diagnostic_json_fails(self):
        client = RecordingClient()
        args = argparse.Namespace(
            event_id='evt-3', run_item_id='item-3', status='failed',
            submission_status='form_in_progress',
            verification_status=None, last_error='error', exact_result=None,
            evidence_reference=None, public_listing_url=None,
            backend_checked_at=None, mailbox_checked_at=None,
            public_page_checked_at=None, follow_up_at=None, follow_up_note=None,
            retry_diagnostic_json='not-json',
        )
        with self.assertRaises(ShipmoreClientError):
            client.complete(args)


if __name__ == '__main__':
    unittest.main()
