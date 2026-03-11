#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime, timezone

import requests

try:
    from .github_issues import create_github_issue
except ImportError:
    from github_issues import create_github_issue

URLS_TO_CHECK = [
    'https://www.zentraleserien-hybridesuche.zh.ch',
    'https://www.zentraleserien.zh.ch/documents/abl/ABl_1966__S__568-589_?norm=on',
]
STATUS_FILE = os.path.join(os.path.dirname(__file__), '..', 'status.json')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'history.json')
REQUEST_HEADERS = {'User-Agent': 'Uptime-Monitor/1.0.0'}
REQUEST_TIMEOUT_SECONDS = 30
RETRY_DELAYS_SECONDS = (15 * 60, 15 * 60)
MAX_HISTORY_RUNS = 1000


def _transport_exception_type():
    exceptions_module = getattr(requests, 'exceptions', None)
    return getattr(exceptions_module, 'RequestException', Exception)


def _is_transport_error(error):
    return isinstance(error, _transport_exception_type())


def _base_status(url):
    return {
        'url': url,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status': 'unknown',
        'responseTime': 0,
        'statusCode': 0,
        'error': None,
        'attemptCount': 1,
        'confirmedFailure': False,
        'message': None,
    }


def _finalize_status(status, final_status, attempt_count, confirmed_failure, message):
    status['status'] = final_status
    status['attemptCount'] = attempt_count
    status['confirmedFailure'] = confirmed_failure
    status['message'] = message
    status.pop('_classification', None)
    status.pop('_failureType', None)
    return status


def _classify_http_status(status_code):
    if 200 <= status_code < 300:
        return 'online', 'none'
    if status_code == 403:
        return 'retryable', '403'
    return 'offline', 'http_status'


def _classify_error(error):
    if _is_transport_error(error):
        return 'retryable', 'transport'
    return 'offline', 'exception'


def _direct_failure_message(status, phase='initial check'):
    if status.get('_failureType') == 'http_status':
        return f"HTTP {status['statusCode']} returned on {phase}"
    if status.get('_failureType') == 'exception':
        return f'Unexpected error during {phase}'
    return 'Website is offline'


def _confirmed_retry_failure_message(attempts):
    failure_types = {attempt.get('_failureType') for attempt in attempts}
    if failure_types == {'403'}:
        return '403 persisted across 3 checks'
    if failure_types == {'transport'}:
        return 'Transport error persisted across 3 checks'
    return 'Retryable failure persisted across 3 checks'


def _recovery_message(attempt_count):
    minutes = (attempt_count - 1) * 15
    return f'Recovered on retry after {minutes} minutes'


def single_check(url, request_get=requests.get):
    start_time = time.time()
    status = _base_status(url)
    try:
        response = request_get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=REQUEST_HEADERS,
        )
        response_time = int((time.time() - start_time) * 1000)
        classification, failure_type = _classify_http_status(response.status_code)
        status.update({
            'responseTime': response_time,
            'statusCode': response.status_code,
            '_classification': classification,
            '_failureType': failure_type,
        })
        if classification == 'online':
            print(f"✅ Website is online - Status: {response.status_code} - Response time: {response_time}ms")
        elif classification == 'retryable':
            print(f"⚠️ Website returned retryable status {response.status_code} - Response time: {response_time}ms")
        else:
            print(f"❌ Website is offline - Status: {response.status_code} - Response time: {response_time}ms")
    except Exception as error:
        response_time = int((time.time() - start_time) * 1000)
        classification, failure_type = _classify_error(error)
        status.update({
            'responseTime': response_time,
            'statusCode': 0,
            'error': str(error),
            '_classification': classification,
            '_failureType': failure_type,
        })
        if classification == 'retryable':
            print(f"⚠️ Retryable transport error: {error}")
        else:
            print(f"❌ Website is offline - Error: {error}")
    return status


def _maybe_create_issue(status):
    if status.get('status') != 'offline' or not status.get('confirmedFailure'):
        return

    repo = os.environ.get('GITHUB_REPOSITORY', 'ruedtim/uptime')
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print('⚠️ No GITHUB_TOKEN found in environment. Cannot create GitHub issue.')
        return

    title = f"Website DOWN: {status['url']}"
    body = (
        f"Automatic alert: The website {status['url']} is down as of {status['timestamp']}.\n\n"
        f"Message: {status.get('message')}\n"
        f"Attempts: {status.get('attemptCount')}\n"
        f"Error: {status.get('error')}\n"
        f"Status code: {status.get('statusCode')}"
    )
    create_github_issue(repo, title, body, token)


def check_url(url, sleep_fn=time.sleep, request_get=requests.get):
    print(f'Checking website: {url}')
    attempts = [single_check(url, request_get=request_get)]
    first_attempt = attempts[0]

    if first_attempt['_classification'] == 'online':
        return _finalize_status(first_attempt, 'online', 1, False, None)

    if first_attempt['_classification'] == 'offline':
        final_status = _finalize_status(first_attempt, 'offline', 1, True, _direct_failure_message(first_attempt))
        _maybe_create_issue(final_status)
        return final_status

    for attempt_count, delay_seconds in enumerate(RETRY_DELAYS_SECONDS, start=2):
        print(f'Retrying in {delay_seconds // 60} minutes...')
        sleep_fn(delay_seconds)
        attempt = single_check(url, request_get=request_get)
        attempts.append(attempt)

        if attempt['_classification'] == 'online':
            return _finalize_status(attempt, 'online', attempt_count, False, _recovery_message(attempt_count))

        if attempt['_classification'] == 'offline':
            final_status = _finalize_status(
                attempt,
                'offline',
                attempt_count,
                True,
                _direct_failure_message(attempt, phase=f'retry attempt {attempt_count}'),
            )
            _maybe_create_issue(final_status)
            return final_status

    final_status = _finalize_status(
        attempts[-1],
        'offline',
        len(attempts),
        True,
        _confirmed_retry_failure_message(attempts),
    )
    _maybe_create_issue(final_status)
    return final_status


def check_websites(sleep_fn=time.sleep, request_get=requests.get):
    return [check_url(url, sleep_fn=sleep_fn, request_get=request_get) for url in URLS_TO_CHECK]


def save_status(statuses):
    """Save the current status list to status.json."""
    try:
        with open(STATUS_FILE, 'w') as file_handle:
            json.dump(statuses, file_handle, indent=2)
        print('Status saved to status.json')
    except Exception as error:
        print(f'Error saving status: {error}')


def _iter_history_entries(history):
    for entry in history:
        if isinstance(entry, dict) and 'url' in entry:
            yield entry
        elif isinstance(entry, dict) and isinstance(entry.get('checks'), list):
            for item in entry['checks']:
                if isinstance(item, dict) and 'url' in item:
                    yield item
        elif isinstance(entry, list):
            for item in entry:
                if isinstance(item, dict) and 'url' in item:
                    yield item


def _trim_history_entries(history):
    max_entries = MAX_HISTORY_RUNS * max(len(URLS_TO_CHECK), 1)
    if len(history) <= max_entries:
        return history
    return history[-max_entries:]


def save_to_history(statuses):
    """Save status to history.json."""
    try:
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as file_handle:
                history = json.load(file_handle)

        history.extend(statuses)
        history = _trim_history_entries(history)

        with open(HISTORY_FILE, 'w') as file_handle:
            json.dump(history, file_handle, indent=2)
        print('Status added to history.json')
    except Exception as error:
        print(f'Error saving to history: {error}')


def calculate_uptime(url=None):
    """Calculate uptime statistics from history."""
    try:
        if not os.path.exists(HISTORY_FILE):
            return {'uptime': '0', 'totalChecks': 0, 'onlineChecks': 0}

        with open(HISTORY_FILE, 'r') as file_handle:
            history = json.load(file_handle)

        entries = [entry for entry in _iter_history_entries(history) if url is None or entry.get('url') == url]
        total_checks = len(entries)
        online_checks = sum(1 for check in entries if check.get('status') == 'online')
        uptime = (online_checks / total_checks) * 100 if total_checks > 0 else 0

        return {
            'uptime': f'{uptime:.2f}',
            'totalChecks': total_checks,
            'onlineChecks': online_checks,
        }
    except Exception as error:
        print(f'Error calculating uptime: {error}')
        return {'uptime': '0', 'totalChecks': 0, 'onlineChecks': 0}


def main():
    """Main function to run the uptime check."""
    print('Starting uptime check...')

    statuses = check_websites()
    save_to_history(statuses)

    for status in statuses:
        status['uptime'] = calculate_uptime(status.get('url'))

    save_status(statuses)

    for status in statuses:
        uptime_stats = status.get('uptime', {})
        print(
            f"Uptime for {status.get('url')}: {uptime_stats.get('uptime', '0')}% "
            f"({uptime_stats.get('onlineChecks', 0)}/{uptime_stats.get('totalChecks', 0)} checks)"
        )
    print('Uptime check completed!')


if __name__ == '__main__':
    main()
