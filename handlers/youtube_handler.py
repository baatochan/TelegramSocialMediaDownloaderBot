
import time
import traceback
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import yt_dlp_wrapper
from handlers.base import MediaHandler, PostData


class YouTubeHandler(MediaHandler):
    SITE_NAME = "youtube"
    URL_REGEX = r"((http(s)?://)|^| )(www\.|m\.)?(youtube(-nocookie)?\.com|youtu\.be)/.+"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        if not self.enabled:
            print("YouTubeHandler is disabled.")

    def normalize_url(self, link: str) -> str:
        parsed = urlsplit(link)
        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        filtered_query_params = [
            (key, value)
            for key, value in query_params
            if key not in {"si", "pp"}
        ]
        normalized_query = urlencode(filtered_query_params, doseq=True)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, normalized_query, ""))

    def handle(self, link: str) -> PostData | None:
        try:
            [output_filename, info_dict] = yt_dlp_wrapper.download(link)
            return self._prepare_metadata(output_filename, info_dict)
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print("Couldn't get video from url: " + link)
            print()
            return None

    def _prepare_metadata(self, output_filename, info_dict) -> PostData:
        return PostData(
            site="youtube",
            post_type="media",
            post_id=info_dict['id'],
            url=info_dict['original_url'],
            author=info_dict['uploader'] +
            " (" + info_dict['uploader_id'] + ")",
            text=info_dict['fulltitle'],
            spoiler=False,
            media=[[output_filename, "video_file"]],
        )
