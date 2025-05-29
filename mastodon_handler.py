import requests
import re
from telebot.formatting import escape_markdown
from html import unescape

def html_to_markdown(text):
    # Replace <br> and <p> with newlines
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p\s*>', '\n', text)
    text = re.sub(r'<p\s*>', '', text)

    # Bold: <strong> or <b>
    text = re.sub(r'<(strong|b)>(.*?)</\1>', r'*\2*', text)
    # Italic: <em> or <i>
    text = re.sub(r'<(em|i)>(.*?)</\1>', r'_\2_', text)
    # Strikethrough: <del>
    text = re.sub(r'<del>(.*?)</del>', r'~\1~', text)
    # Inline code: <code>
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)

    # Links: <a href="...">text</a>
    def link_replacer(match):
        url = match.group(1)
        label = match.group(2)
        # Escape label and url for MarkdownV2
        from telebot.formatting import escape_markdown
        label_escaped = escape_markdown(unescape(label))
        url_escaped = escape_markdown(unescape(url))
        return f'[{label_escaped}]({url_escaped})'
    text = re.sub(r'<a href="([^"]+)".*?>(.*?)</a>', link_replacer, text)

    # Remove all other tags
    text = re.sub(r'<[^>]+>', '', text)
    # Unescape HTML entities
    text = unescape(text)
    # Escape for Telegram MarkdownV2 (except links, already escaped)
    text = escape_markdown(text)
    # But unescape already escaped links (avoid double escaping)
    text = re.sub(r'\\\[(.*?)\\\]\(\\\((.*?)\\\)\)', r'[\1](\2)', text)
    return text.strip()

def html_to_clean_text(text):
    # Replace <br> and </p> with newlines, remove <p>
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p\s*>', '', text, flags=re.IGNORECASE)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Unescape HTML entities
    text = unescape(text)
    # Remove extra consecutive newlines
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()

def handle_url(url):
    m = re.match(r"https?://([^/]+)/@[^/]+/(\d+)", url)
    if not m:
        return {}
    domain, status_id = m.groups()
    # Try v2 API first, then v1
    for api_version in ["v2", "v1"]:
        api_url = f"https://{domain}/api/{api_version}/statuses/{status_id}"
        try:
            resp = requests.get(api_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                handler_response = {
                    "type": "media" if data.get("media_attachments") else "text",
                    "site": "mastodon",
                    "text": html_to_clean_text(data.get("content", "")),
                    "author": data.get("account", {}).get("acct", ""),
                    "url": url,
                    "media": [],
                    "spoiler": False,
                }
                for media in data.get("media_attachments", []):
                    if media["type"] == "image":
                        handler_response["media"].append((media["url"], "photo"))
                    elif media["type"] == "video" or media["type"] == "gifv":
                        handler_response["media"].append((media["url"], "video"))
                return handler_response
        except Exception as e:
            print(f"Error fetching Mastodon post from {api_url}: {e}")
    return {}