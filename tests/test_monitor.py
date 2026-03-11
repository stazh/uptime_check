import importlib
import sys
import types
import unittest
from collections import Counter
from unittest.mock import patch


fake_requests = types.ModuleType('requests')


class RequestException(Exception):
    pass


def _unused_request(*args, **kwargs):
    raise AssertionError('Unexpected real network call during tests')


fake_requests.exceptions = types.SimpleNamespace(RequestException=RequestException)
fake_requests.get = _unused_request
fake_requests.post = _unused_request
sys.modules.setdefault('requests', fake_requests)

monitor = importlib.import_module('src.monitor')


class Response:
    def __init__(self, status_code):
        self.status_code = status_code


class TransportError(RequestException):
    pass


def sequence_request(results):
    items = list(results)

    def request_get(url, timeout, headers):
        if not items:
            raise AssertionError('No more test responses available')
        next_item = items.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    return request_get


class MonitorTests(unittest.TestCase):
    def test_online_on_first_success(self):
        sleep_calls = []

        with patch.object(monitor, '_maybe_create_issue') as issue_mock:
            status = monitor.check_url(
                'https://example.com',
                sleep_fn=sleep_calls.append,
                request_get=sequence_request([Response(200)]),
            )

        self.assertEqual(status['status'], 'online')
        self.assertEqual(status['attemptCount'], 1)
        self.assertFalse(status['confirmedFailure'])
        self.assertIsNone(status['message'])
        self.assertEqual(sleep_calls, [])
        issue_mock.assert_not_called()

    def test_403_recovers_on_second_attempt(self):
        sleep_calls = []

        with patch.object(monitor, '_maybe_create_issue') as issue_mock:
            status = monitor.check_url(
                'https://example.com',
                sleep_fn=sleep_calls.append,
                request_get=sequence_request([Response(403), Response(200)]),
            )

        self.assertEqual(status['status'], 'online')
        self.assertEqual(status['attemptCount'], 2)
        self.assertEqual(status['message'], 'Recovered on retry after 15 minutes')
        self.assertEqual(sleep_calls, [900])
        issue_mock.assert_not_called()

    def test_403_three_times_confirms_offline(self):
        sleep_calls = []

        with patch.object(monitor, '_maybe_create_issue') as issue_mock:
            status = monitor.check_url(
                'https://example.com',
                sleep_fn=sleep_calls.append,
                request_get=sequence_request([Response(403), Response(403), Response(403)]),
            )

        self.assertEqual(status['status'], 'offline')
        self.assertEqual(status['attemptCount'], 3)
        self.assertTrue(status['confirmedFailure'])
        self.assertEqual(status['message'], '403 persisted across 3 checks')
        self.assertEqual(sleep_calls, [900, 900])
        issue_mock.assert_called_once_with(status)

    def test_transport_error_recovers_on_third_attempt(self):
        sleep_calls = []

        with patch.object(monitor, '_maybe_create_issue') as issue_mock:
            status = monitor.check_url(
                'https://example.com',
                sleep_fn=sleep_calls.append,
                request_get=sequence_request([
                    TransportError('network down'),
                    TransportError('network down'),
                    Response(200),
                ]),
            )

        self.assertEqual(status['status'], 'online')
        self.assertEqual(status['attemptCount'], 3)
        self.assertEqual(status['message'], 'Recovered on retry after 30 minutes')
        self.assertEqual(sleep_calls, [900, 900])
        issue_mock.assert_not_called()

    def test_transport_error_three_times_confirms_offline(self):
        sleep_calls = []

        with patch.object(monitor, '_maybe_create_issue') as issue_mock:
            status = monitor.check_url(
                'https://example.com',
                sleep_fn=sleep_calls.append,
                request_get=sequence_request([
                    TransportError('network down'),
                    TransportError('network down'),
                    TransportError('still down'),
                ]),
            )

        self.assertEqual(status['status'], 'offline')
        self.assertEqual(status['attemptCount'], 3)
        self.assertTrue(status['confirmedFailure'])
        self.assertEqual(status['message'], 'Transport error persisted across 3 checks')
        self.assertEqual(sleep_calls, [900, 900])
        issue_mock.assert_called_once_with(status)

    def test_non_retryable_http_error_is_immediately_offline(self):
        sleep_calls = []

        with patch.object(monitor, '_maybe_create_issue') as issue_mock:
            status = monitor.check_url(
                'https://example.com',
                sleep_fn=sleep_calls.append,
                request_get=sequence_request([Response(500)]),
            )

        self.assertEqual(status['status'], 'offline')
        self.assertEqual(status['attemptCount'], 1)
        self.assertTrue(status['confirmedFailure'])
        self.assertEqual(status['message'], 'HTTP 500 returned on initial check')
        self.assertEqual(sleep_calls, [])
        issue_mock.assert_called_once_with(status)

    def test_trim_history_keeps_both_urls(self):
        history = []
        for run_number in range(monitor.MAX_HISTORY_RUNS + 1):
            for url in monitor.URLS_TO_CHECK:
                history.append({'url': url, 'status': 'online', 'run': run_number})

        trimmed = monitor._trim_history_entries(history)

        self.assertEqual(len(trimmed), monitor.MAX_HISTORY_RUNS * len(monitor.URLS_TO_CHECK))
        counts = Counter(entry['url'] for entry in trimmed)
        for url in monitor.URLS_TO_CHECK:
            self.assertEqual(counts[url], monitor.MAX_HISTORY_RUNS)


if __name__ == '__main__':
    unittest.main()
