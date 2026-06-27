
import re
import time
import traceback
import yt_dlp_wrapper
from handlers.base import MediaHandler, PostData


class YouTubeHandler(MediaHandler):
    def handle(self, link: str) -> PostData | None:
        clean_link = self._clean_up_url(link)
        try:
            [output_filename, info_dict] = yt_dlp_wrapper.download(clean_link)
            return self._prepare_metadata(output_filename, info_dict)
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print("Couldn't get video from url: " + link)
            print()
            return None

    def _clean_up_url(self, link: str) -> str:
        link = re.sub(r"si=([\w\-_]*)", "", link)  # Remove si parameter
        link = re.sub(r"[?&]+$", "", link)  # Remove trailing "?" or "&"
        link = re.sub(r"&+", "&", link)  # Remove multiple "&"
        link = re.sub(r"\?&", "?", link)  # Replace ?& with ?
        return link

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
