import time
import traceback
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse
from urllib.request import urlretrieve


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

        urlretrieve(url, temp_path)

        # Another worker may create final_path while this download is in progress.
        if final_path.is_file():
            fallback_path = site_dir / f"{post_id}.{uuid4().hex}{ext}"
            temp_path.rename(fallback_path)
            return str(fallback_path)

        temp_path.rename(final_path)
        return str(final_path)
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print("Couldn't download video from url: " + url)
        print()
        return ""
