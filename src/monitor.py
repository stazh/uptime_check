#!/usr/bin/env python3

import requests
import json
import os
from datetime import datetime, timezone
import time
from github_issues import create_github_issue

URLS_TO_CHECK = [
    'https://www.zentraleserien-hybridesuche.zh.ch',
    'https://www.zentraleserien.zh.ch/documents/abl/ABl_1966__S__568-589_?norm=on',
]
STATUS_FILE = os.path.join(os.path.dirname(__file__), '..', 'status.json')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), '..', 'history.json')

def single_check(url):
    start_time = time.time()
    status = {
        'url': url,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status': 'unknown',
        'responseTime': 0,
        'statusCode': 0,
        'error': None
    }
    try:
        response = requests.get(
            url,
            timeout=30,
            headers={'User-Agent': 'Uptime-Monitor/1.0.0'}
        )
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)
        status.update({
            'status': 'online' if 200 <= response.status_code < 300 else 'offline',
            'responseTime': response_time,
            'statusCode': response.status_code
        })
        print(f"✅ Website is online - Status: {response.status_code} - Response time: {response_time}ms")
    except Exception as error:
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)
        status.update({
            'status': 'offline',
            'responseTime': response_time,
            'statusCode': 0,
            'error': str(error)
        })
        print(f"❌ Website is offline - Error: {error}")
    return status

def check_url(url):
    """Check if the website is online and return status information. Retry once if offline."""
    print(f"Checking website: {url}")
    status = single_check(url)
    if status['status'] == 'offline':
        print("Retrying after failure...")
        time.sleep(5)
        status = single_check(url)
        if status['status'] == 'offline':
            # Open GitHub issue if still offline
            repo = os.environ.get('GITHUB_REPOSITORY', 'ruedtim/uptime')
            token = os.environ.get('GITHUB_TOKEN')
            if token:
                title = f"Website DOWN: {url}"
                body = f"Automatic alert: The website {url} is down as of {status['timestamp']}.\n\nError: {status['error']}\nStatus code: {status['statusCode']}"
                create_github_issue(repo, title, body, token)
            else:
                print("⚠️ No GITHUB_TOKEN found in environment. Cannot create GitHub issue.")
    return status

def check_websites():
    return [check_url(url) for url in URLS_TO_CHECK]

def save_status(statuses):
    """Save the current status to status.json"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(statuses, f, indent=2)
        print('Status saved to status.json')
    except Exception as error:
        print(f'Error saving status: {error}')

def save_to_history(statuses):
    """Save status to history.json"""
    try:
        history = []
        
        # Read existing history if file exists
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        
        # Add new status entries to history
        history.extend(statuses)
        
        # Keep only last 1000 entries to prevent file from growing too large
        if len(history) > 1000:
            history = history[-1000:]
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        print('Status added to history.json')
        
    except Exception as error:
        print(f'Error saving to history: {error}')

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

def calculate_uptime(url=None):
    """Calculate uptime statistics from history"""
    try:
        if not os.path.exists(HISTORY_FILE):
            return {'uptime': '0', 'totalChecks': 0, 'onlineChecks': 0}
        
        with open(HISTORY_FILE, 'r') as f:
            history = json.load(f)

        entries = [entry for entry in _iter_history_entries(history) if url is None or entry.get('url') == url]
        total_checks = len(entries)
        online_checks = sum(1 for check in entries if check.get('status') == 'online')
        uptime = (online_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return {
            'uptime': f"{uptime:.2f}",
            'totalChecks': total_checks,
            'onlineChecks': online_checks
        }
        
    except Exception as error:
        print(f'Error calculating uptime: {error}')
        return {'uptime': '0', 'totalChecks': 0, 'onlineChecks': 0}

def main():
    """Main function to run the uptime check"""
    print('Starting uptime check...')
    
    statuses = check_websites()
    
    save_to_history(statuses)

    # Add uptime statistics to each status (after history update)
    for status in statuses:
        status['uptime'] = calculate_uptime(status.get('url'))
    
    save_status(statuses)
    
    for status in statuses:
        uptime_stats = status.get('uptime', {})
        print(f"Uptime for {status.get('url')}: {uptime_stats.get('uptime', '0')}% ({uptime_stats.get('onlineChecks', 0)}/{uptime_stats.get('totalChecks', 0)} checks)")
    print('Uptime check completed!')

if __name__ == "__main__":
    main()
