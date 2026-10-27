#!/usr/bin/env python3

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from directory_admin_client import (  # noqa: E402
    SHIPMORE_API_KEY_ENV,
    DirectoryAdminClient,
    DirectoryAdminError,
    OBSERVED_PRICING_PRIORITY,
    admin_sync_note,
    build_parser,
    map_observed_pricing,
    maybe_reject_after_unavailable,
    read_local_unavailable_streak,
    record_unavailable_outcome,
    reset_unavailable_streak,
    resolve_admin_api_key,
    resolve_observed_pricing,
    sync_pricing_if_mismatch,
)


class FakeHTTPResponse:
    def __init__(self, body: str, status: int = 200):
        self._body = body.encode('utf-8')
        self.status = status

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DirectoryAdminClientTests(unittest.TestCase):
    def test_map_observed_pricing_aliases(self):
        self.assertEqual(map_observed_pricing('free listing'), 'free')
        self.assertEqual(map_observed_pricing('free_queue'), 'free')
        self.assertEqual(map_observed_pricing('paid_only'), 'paid')
        self.assertEqual(map_observed_pricing('expedite'), 'paid')
        self.assertEqual(map_observed_pricing('reciprocal'), 'backlink')
        self.assertEqual(map_observed_pricing('badge_required'), 'backlink')
        with self.assertRaises(DirectoryAdminError):
            map_observed_pricing('unknown-tier')

    def test_map_observed_pricing_accepts_spaced_free_listing(self):
        # True free path: no payment and no badge/reciprocal/backlink requirement.
        self.assertEqual(map_observed_pricing('free'), 'free')
        self.assertEqual(map_observed_pricing('FREE'), 'free')
        self.assertEqual(map_observed_pricing('$0'), 'free')

    def test_map_observed_pricing_free_plus_badge_is_backlink(self):
        # Site may label the path Free/$0; badge/reciprocal/backlink still means
        # observed directoryPricing is backlink, never free.
        self.assertEqual(map_observed_pricing('free with badge'), 'backlink')
        self.assertEqual(map_observed_pricing('free+badge'), 'backlink')
        self.assertEqual(map_observed_pricing('free_badge_required'), 'backlink')
        self.assertEqual(map_observed_pricing('$0 badge required'), 'backlink')
        self.assertEqual(map_observed_pricing('$0 + badge'), 'backlink')
        self.assertEqual(map_observed_pricing('free reciprocal'), 'backlink')
        self.assertEqual(map_observed_pricing('free listing with backlink'), 'backlink')
        self.assertEqual(map_observed_pricing('free link back'), 'backlink')

    def test_map_observed_pricing_true_free_without_badge(self):
        self.assertEqual(map_observed_pricing('free'), 'free')
        self.assertEqual(map_observed_pricing('free listing'), 'free')
        self.assertEqual(map_observed_pricing('free_submit'), 'free')
        self.assertEqual(map_observed_pricing('free_queue'), 'free')

    def test_observed_pricing_priority_constant(self):
        self.assertEqual(OBSERVED_PRICING_PRIORITY, ('free', 'backlink', 'paid'))

    def test_resolve_observed_pricing_prefers_free_over_paid_and_backlink(self):
        # Separate true-free path still beats distinct backlink and paid paths.
        self.assertEqual(
            resolve_observed_pricing(['free', 'paid', 'backlink']),
            'free',
        )
        self.assertEqual(
            resolve_observed_pricing('free_listing,expedite,reciprocal'),
            'free',
        )
        self.assertEqual(
            resolve_observed_pricing(['paid', 'free_submit']),
            'free',
        )

    def test_resolve_observed_pricing_prefers_backlink_over_paid(self):
        self.assertEqual(
            resolve_observed_pricing(['backlink', 'paid']),
            'backlink',
        )
        self.assertEqual(
            resolve_observed_pricing('badge_required,paid_tier,expedite'),
            'backlink',
        )
        self.assertEqual(
            resolve_observed_pricing(['paid_only', 'reciprocal_link']),
            'backlink',
        )

    def test_resolve_observed_pricing_zero_plus_badge_does_not_win_as_free(self):
        # Classify $0+badge as backlink before priority; it must not beat paid
        # by falsely mapping to free, and must beat paid as backlink.
        self.assertEqual(
            resolve_observed_pricing(['$0 badge required', 'paid']),
            'backlink',
        )
        self.assertEqual(
            resolve_observed_pricing('free with badge,expedite'),
            'backlink',
        )
        # A true free path alongside a $0+badge path still correctly wins as free.
        self.assertEqual(
            resolve_observed_pricing(['free listing', 'free with badge', 'paid']),
            'free',
        )

    def test_resolve_observed_pricing_paid_only_when_no_higher_path(self):
        self.assertEqual(resolve_observed_pricing('paid'), 'paid')
        self.assertEqual(resolve_observed_pricing(['expedite', 'paid_tier']), 'paid')

    def test_resolve_admin_api_key_prefers_shipmore_api_key(self):
        with patch.dict(
            os.environ,
            {
                SHIPMORE_API_KEY_ENV: 'personal-key',
                'DIRECTORY_ADMIN_API_TOKEN': 'legacy-secret',
            },
            clear=False,
        ):
            self.assertEqual(resolve_admin_api_key(), 'personal-key')

    def test_resolve_admin_api_key_legacy_fallback_warns(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(SHIPMORE_API_KEY_ENV, None)
            os.environ['DIRECTORY_ADMIN_API_TOKEN'] = 'legacy-secret'
            import directory_admin_client as dac

            dac._ADMIN_DEPRECATION_WARNED = False
            with patch('sys.stderr', new=io.StringIO()) as err:
                self.assertEqual(resolve_admin_api_key(), 'legacy-secret')
                self.assertIn('deprecated', err.getvalue().lower())

    def test_sync_pricing_applies_multi_path_priority(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured['body'] = json.loads(request.data.decode('utf-8'))
            return FakeHTTPResponse('{"ok":true}', status=200)

        with patch('directory_admin_client.urlopen', side_effect=fake_urlopen):
            result = sync_pricing_if_mismatch(
                client,
                directory_id='dir-priority',
                claim_pricing='paid',
                observed_pricing='paid,backlink,free',
            )
        self.assertTrue(result['mismatch'])
        self.assertEqual(result['observedPricing'], 'free')
        self.assertEqual(captured['body']['pricing'], 'free')

    def test_admin_sync_note_never_embeds_secrets(self):
        note = admin_sync_note('pricing', ok=False, status_code=401)
        self.assertEqual(note, 'admin pricing sync failed: HTTP 401')
        self.assertNotIn('Bearer', note)
        self.assertNotIn('admin-secret', note)
        missing = admin_sync_note('pricing', ok=False, status_code=None)
        self.assertIn('missing API key', missing)

    def test_update_directory_pricing_patch(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured['url'] = request.full_url
            captured['method'] = request.get_method()
            captured['headers'] = dict(request.headers)
            captured['body'] = json.loads(request.data.decode('utf-8'))
            return FakeHTTPResponse('{"success":true}', status=200)

        with patch('directory_admin_client.urlopen', side_effect=fake_urlopen):
            result = client.update_directory('dir-1', pricing='paid')

        self.assertTrue(result['ok'])
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(captured['url'], 'https://shipmore.example/api/admin/directories')
        self.assertEqual(captured['method'], 'PATCH')
        header_items = {
            str(k).lower(): v for k, v in captured['headers'].items()
        }
        self.assertEqual(header_items.get('x-api-key'), 'admin-secret')
        self.assertNotIn('authorization', header_items)
        self.assertEqual(
            captured['body'],
            {'directoryId': 'dir-1', 'pricing': 'paid'},
        )
        self.assertEqual(result['note'], 'admin pricing sync ok')

    def test_update_directory_status_endpoint(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured['url'] = request.full_url
            captured['body'] = json.loads(request.data.decode('utf-8'))
            return FakeHTTPResponse('{}', status=204)

        with patch('directory_admin_client.urlopen', side_effect=fake_urlopen):
            result = client.update_directory_status('dir-2', 'rejected')

        self.assertTrue(result['ok'])
        self.assertEqual(
            captured['url'],
            'https://shipmore.example/api/admin/directories/status',
        )
        self.assertEqual(
            captured['body'],
            {'directoryId': 'dir-2', 'status': 'rejected'},
        )
        self.assertEqual(result['note'], 'admin status sync ok')

    def test_http_error_returns_status_only_note(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')

        def fake_urlopen(request, timeout=30):
            raise HTTPError(
                request.full_url,
                401,
                'Unauthorized',
                hdrs=None,
                fp=io.BytesIO(b'{"error":"unauthorized"}'),
            )

        with patch('directory_admin_client.urlopen', side_effect=fake_urlopen):
            result = client.update_directory('dir-1', pricing='free')

        self.assertFalse(result['ok'])
        self.assertEqual(result['statusCode'], 401)
        self.assertEqual(result['note'], 'admin pricing sync failed: HTTP 401')
        dumped = json.dumps(result)
        self.assertNotIn('admin-secret', dumped)

    def test_network_error_note(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')

        def fake_urlopen(request, timeout=30):
            raise URLError('dns failure')

        with patch('directory_admin_client.urlopen', side_effect=fake_urlopen):
            result = client.update_directory_status('dir-1', 'rejected')

        self.assertFalse(result['ok'])
        self.assertIsNone(result['statusCode'])
        self.assertIn('failed', result['note'])

    def test_sync_pricing_skips_when_matching(self):
        result = sync_pricing_if_mismatch(
            None,
            directory_id='dir-1',
            claim_pricing='free',
            observed_pricing='free',
        )
        self.assertFalse(result['mismatch'])
        self.assertFalse(result['synced'])
        self.assertIsNone(result['note'])

    def test_sync_pricing_mismatch_without_token(self):
        result = sync_pricing_if_mismatch(
            None,
            directory_id='dir-1',
            claim_pricing='free',
            observed_pricing='paid',
        )
        self.assertTrue(result['mismatch'])
        self.assertFalse(result['synced'])
        self.assertEqual(
            result['note'],
            'admin pricing sync failed: missing API key or network error',
        )

    def test_sync_pricing_mismatch_calls_patch(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')

        def fake_urlopen(request, timeout=30):
            return FakeHTTPResponse('{"ok":true}', status=200)

        with patch('directory_admin_client.urlopen', side_effect=fake_urlopen):
            result = sync_pricing_if_mismatch(
                client,
                directory_id='dir-9',
                claim_pricing='free',
                observed_pricing='backlink',
            )
        self.assertTrue(result['mismatch'])
        self.assertTrue(result['synced'])
        self.assertEqual(result['observedPricing'], 'backlink')
        self.assertEqual(result['note'], 'admin pricing sync ok')

    def test_unavailable_streak_rejects_on_third(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                'os.environ',
                {'SHIPMORE_DIRECTORY_UNAVAILABLE_DIR': tmp},
                clear=False,
            ):
                first = record_unavailable_outcome('dir-a')
                second = record_unavailable_outcome('dir-a')
                third = record_unavailable_outcome('dir-a')
                self.assertEqual(first['consecutiveUnavailable'], 1)
                self.assertFalse(first['shouldRejectDirectory'])
                self.assertEqual(second['consecutiveUnavailable'], 2)
                self.assertFalse(second['shouldRejectDirectory'])
                self.assertEqual(third['consecutiveUnavailable'], 3)
                self.assertTrue(third['shouldRejectDirectory'])
                self.assertEqual(read_local_unavailable_streak('dir-a'), 3)

                reset = reset_unavailable_streak('dir-a')
                self.assertEqual(reset['consecutiveUnavailable'], 0)
                self.assertEqual(read_local_unavailable_streak('dir-a'), 0)

    def test_shipmore_backed_count_preferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                'os.environ',
                {'SHIPMORE_DIRECTORY_UNAVAILABLE_DIR': tmp},
                clear=False,
            ):
                result = record_unavailable_outcome(
                    'dir-b',
                    shipmore_consecutive_count=3,
                )
                self.assertEqual(result['consecutiveUnavailable'], 3)
                self.assertEqual(result['source'], 'shipmore')
                self.assertTrue(result['shouldRejectDirectory'])

    def test_maybe_reject_calls_status_endpoint_on_threshold(self):
        client = DirectoryAdminClient('https://shipmore.example', 'admin-secret')
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured['url'] = request.full_url
            captured['body'] = json.loads(request.data.decode('utf-8'))
            return FakeHTTPResponse('{}', status=200)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                'os.environ',
                {'SHIPMORE_DIRECTORY_UNAVAILABLE_DIR': tmp},
                clear=False,
            ):
                with patch(
                    'directory_admin_client.urlopen', side_effect=fake_urlopen
                ):
                    result = maybe_reject_after_unavailable(
                        client,
                        directory_id='dir-c',
                        shipmore_consecutive_count=3,
                    )
        self.assertTrue(result['shouldRejectDirectory'])
        self.assertTrue(result['rejected'])
        self.assertEqual(
            captured['url'],
            'https://shipmore.example/api/admin/directories/status',
        )
        self.assertEqual(
            captured['body'],
            {'directoryId': 'dir-c', 'status': 'rejected'},
        )

    def test_parser_exposes_admin_commands(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                'admin-update-directory',
                '--directory-id',
                'd1',
                '--pricing',
                'paid',
            ]
        )
        self.assertEqual(args.command, 'admin-update-directory')
        self.assertEqual(args.pricing, 'paid')
        args2 = parser.parse_args(
            [
                'admin-update-directory-status',
                '--directory-id',
                'd1',
                '--status',
                'rejected',
            ]
        )
        self.assertEqual(args2.command, 'admin-update-directory-status')


if __name__ == '__main__':
    unittest.main()
