import requests

def handle_url(url):
    # Extract status ID from URL, fetch post via Mastodon API, and return handler_response dict
    # Example Mastodon post: https://mastodon.social/@user/123456789012345678
    import re
    m = re.match(r"https?://([^/]+)/@[^/]+/(\d+)", url)
    if not m:
        return {}
    domain, status_id = m.groups()
    api_url = f"https://{domain}/api/v1/statuses/{status_id}"
    try:
        resp = requests.get(api_url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # Build handler_response similar to other handlers
            handler_response = {
                "type": "media" if data.get("media_attachments") else "text",
                "site": "mastodon",
                "text": data.get("content", ""),
                "author": data.get("account", {}).get("acct", ""),
                "url": url,
                "media": [],
                "spoiler": False,
            }
            for media in data.get("media_attachments", []):
                if media["type"] == "image":
                    handler_response["media"].append((media["url"], "photo"))
                elif media["type"] == "video":
                    handler_response["media"].append((media["url"], "video"))
            return handler_response
    except Exception as e:
        print(f"Error fetching Mastodon post: {e}")
    return {}