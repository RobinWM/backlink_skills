#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from shipmore_queue_client import ShipmoreClientError, ShipmoreQueueClient  # noqa: E402


class RecordingClient(ShipmoreQueueClient):
    def __init__(self, worker_id: str | None = 'worker-01'):
        super().__init__(
            base_url='https://shipmore.example',
            token='test-token',
            worker_id=worker_id,
        )
        self.last_payload = None

    def post(self, payload):
        self.last_payload = payload
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


if __name__ == '__main__':
    unittest.main()
