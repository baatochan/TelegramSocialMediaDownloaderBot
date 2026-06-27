import json
import re
import time
import traceback

import requests
from bs4 import BeautifulSoup
from getuseragent import UserAgent
from selenium import webdriver

from handlers.base import MediaHandler, PostData


class NineGagHandler(MediaHandler):
    SITE_NAME = "9gag"
    URL_REGEX = r"((http(s)?://)|^| )(www\.)?9gag\.com/.+"

    def __init__(self, use_selenium: bool = True):
        self.use_selenium = use_selenium

    def handle(self, link: str) -> PostData | None:
        try:
            if self.use_selenium:
                page_source = self._handle_url_with_selenium(link)
            else:
                page_source = self._handle_url_with_requests(link)

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
                    return self._check_media_type(loaded_json['data']['post'])
        except Exception as e:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            traceback.print_exception(type(e), e, e.__traceback__)
            print()
            return None

        # If parsing succeeds but payload is incomplete.
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        print("9gag returned incomplete json data.")
        return None

    def _handle_url_with_selenium(self, link: str):
        ff_options = webdriver.FirefoxOptions()
        ff_options.add_argument("--headless")
        browser = webdriver.Firefox(options=ff_options)
        browser.get(link)
        source = browser.page_source
        browser.quit()
        return source

    def _handle_url_with_requests(self, link: str):
        user_agent = UserAgent().Random()
        headers = {'User-Agent': user_agent}
        response = requests.get(link, headers=headers)
        return response.content.decode()

    def _check_media_type(self, post_json_data) -> PostData | None:
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
