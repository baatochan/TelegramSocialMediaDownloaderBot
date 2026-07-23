import time
import traceback
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse
import requests


DOWNLOAD_TIMEOUT = (8, 45)
MAX_ATTEMPTS = 3
CHUNK_SIZE = 1024 * 256
RETRY_DELAY_SECONDS = 1.0


def _build_headers(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""

    return {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "video/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": origin or "https://www.google.com/",
        "Origin": origin,
        "Connection": "keep-alive",
    }


def _download_with_retries(url: str, temp_path: Path) -> None:
    headers = _build_headers(url)
    with requests.Session() as session:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = session.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=DOWNLOAD_TIMEOUT,
                    allow_redirects=True,
                )
                with response:
                    response.raise_for_status()

                    with temp_path.open("wb") as fp:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                fp.write(chunk)

                return
            except requests.RequestException:
                if attempt >= MAX_ATTEMPTS:
                    raise
                time.sleep(RETRY_DELAY_SECONDS)


def download_video(url: str, site: str, post_id: str) -> str:
    parsed_path = urlparse(url).path
    ext = Path(parsed_path).suffix or ".mp4"
    site_dir = Path("temp") / site
    final_path = site_dir / f"{post_id}{ext}"
    temp_path = site_dir / f"{post_id}.{uuid4().hex}.tmp{ext}"

    try:
        site_dir.mkdir(parents=True, exist_ok=True)

        if final_path.is_file():
            return str(final_path)

        _download_with_retries(url, temp_path)

        # Another worker may create final_path while this download is in progress.
        if final_path.is_file():
            fallback_path = site_dir / f"{post_id}.{uuid4().hex}{ext}"
            temp_path.rename(fallback_path)
            return str(fallback_path)

        temp_path.rename(final_path)
        return str(final_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print("Couldn't download video from url: " + url)
        print()
        return ""
