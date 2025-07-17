import os
import requests

def create_github_issue(repo, title, body, token):
    """Create a GitHub issue in the given repository."""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    data = {"title": title, "body": body}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        print(f"✅ Issue created: {response.json()['html_url']}")
        return response.json()['html_url']
    else:
        print(f"❌ Failed to create issue: {response.status_code} {response.text}")
        return None
