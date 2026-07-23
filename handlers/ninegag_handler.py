import json
import re
import time
import traceback

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from selenium import webdriver
from urllib3.util.retry import Retry

from handlers.base import MediaHandler, PostData


class NineGagHandler(MediaHandler):
    SITE_NAME = "9gag"
    URL_REGEX = r"((http(s)?://)|^| )(www\.)?9gag\.com/.+"
    REQUEST_TIMEOUT = (8, 25)

    def __init__(self, use_selenium: bool = True):
        self.use_selenium = use_selenium
        self.session: requests.Session | None = None

        if not self.use_selenium:
            self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        retry = Retry(
            total=3,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def handle(self, link: str) -> PostData | None:
        try:
            page_source = self._fetch_page_source(link)

            post_json_data = self._extract_post_json_from_page_source(
                page_source)
            if post_json_data is None:
                print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
                print("9gag returned incomplete json data.")
                return None

            return self._build_post_data_from_post_json(post_json_data)
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print()
            return None

    def _fetch_page_source(self, link: str) -> str:
        if self.use_selenium:
            return self._fetch_page_with_selenium(link)
        return self._fetch_page_with_requests(link)

    def _fetch_page_with_selenium(self, link: str):
        ff_options = webdriver.FirefoxOptions()
        ff_options.add_argument("--headless")
        browser = webdriver.Firefox(options=ff_options)
        browser.get(link)
        source = browser.page_source
        browser.quit()
        return source

    def _fetch_page_with_requests(self, link: str) -> str:
        if self.session is None:
            self.session = self._create_session()

        response = self.session.get(link, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text

    def _extract_post_json_from_page_source(self, page_source: str):
        soup = BeautifulSoup(page_source, 'html.parser')
        for script in soup.find_all('script', attrs={"type": "text/javascript"}):
            if "window._config = JSON.parse" in script.get_text():
                json_text = script.get_text()

                # Remove single backslashes while keeping escaped backslashes.
                json_text = re.sub(r'\\(?!\\)', '', json_text)
                json_text = json_text.replace("\\\\", "\\")

                # Extract only raw JSON from the surrounding JS expression.
                json_text = json_text.replace(
                    "window._config = JSON.parse(\"", "")
                json_text = json_text.replace("\");", "")

                loaded_json = json.loads(json_text)
                return loaded_json['data']['post']

        return None

    def _build_post_data_from_post_json(self, post_json_data) -> PostData | None:
        match post_json_data['type']:
            case "Photo":
                return self._handle_picture(post_json_data)
            case "Animated":
                return self._handle_video(post_json_data)
            case _:
                print(str(time.time()))
                print(post_json_data['type'])
                json_formatted_str = json.dumps(post_json_data, indent=2)
                with open(str(time.time()), "w") as f:
                    f.write(json_formatted_str)
                return None

    def _handle_picture(self, post_json_data) -> PostData | None:
        post_data = PostData(
            site="9gag",
            post_type="media",
            post_id=post_json_data['id'],
            url=post_json_data['url'],
            text=post_json_data['title'],
            spoiler=False,
        )

        if "image700" in post_json_data['images']:
            post_data.media = [
                [post_json_data['images']['image700']['url'], "photo"]]
            return post_data
        if "image460" in post_json_data['images']:
            post_data.media = [
                [post_json_data['images']['image460']['url'], "photo"]]
            return post_data

        return None

    def _handle_video(self, post_json_data) -> PostData | None:
        post_data = PostData(
            site="9gag",
            post_type="media",
            post_id=post_json_data['id'],
            url=post_json_data['url'],
            text=post_json_data['title'],
            spoiler=False,
        )

        if "image700sv" in post_json_data['images']:
            video_type = "video"
            if post_json_data['images']['image700sv']['hasAudio'] == 0 and post_json_data['images']['image700sv']['duration'] <= 20:
                video_type = "gif"
            post_data.media = [
                [post_json_data['images']['image700sv']['url'], video_type]]
            return post_data

        if "image460sv" in post_json_data['images']:
            video_type = "video"
            if post_json_data['images']['image460sv']['hasAudio'] == 0 and post_json_data['images']['image460sv']['duration'] <= 20:
                video_type = "gif"
            post_data.media = [
                [post_json_data['images']['image460sv']['url'], video_type]]
            return post_data

        return None
