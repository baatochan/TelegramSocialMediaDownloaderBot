import json
import time
import traceback

import requests
from bs4 import BeautifulSoup
from getuseragent import UserAgent
from selenium import webdriver


def handle_url(link, use_selenium=True):
    try:
        if (use_selenium):
            page_source = handle_url_with_selenium(link)
        else:
            page_source = handle_url_with_requests(link)

        soup = BeautifulSoup(page_source, 'html.parser')
        for script in soup.find_all('script', attrs={"type": "text/javascript"}):
            if "window._config = JSON.parse" in script.get_text():
                script_json_text = script.get_text()
                # TODO: clean it up, the following 3 lines are the only way I found to remove single backslashes, while keeping double ones as a single one
                script_json_text = script_json_text.replace(
                    "\\\\", "420<impossible-to-happean-naturally-string>2137")
                script_json_text = script_json_text.replace("\\", "")
                script_json_text = script_json_text.replace(
                    "420<impossible-to-happean-naturally-string>2137", "\\")
                # remove beginning and the end of the json to extract only json content
                script_json_text = script_json_text.replace(
                    "window._config = JSON.parse(\"", "")
                script_json_text = script_json_text.replace("\");", "")
                script_json_content = json.loads(script_json_text)
                return check_media_type(script_json_content['data']['post'])
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print()
        return {}

    # if no exception and incomplete data returned by 9gag
    print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
    print("9gag returned incomplete json data.")
    return {}


def handle_url_with_selenium(link):
    ff_options = webdriver.FirefoxOptions()
    ff_options.add_argument("--headless")
    browser = webdriver.Firefox(options=ff_options)
    browser.get(link)
    source = browser.page_source
    browser.quit()
    return source


def handle_url_with_requests(link):
    user_agent = UserAgent().Random()
    headers = {'User-Agent': user_agent}
    response = requests.get(link, headers=headers)
    return response.content.decode()


def check_media_type(post_json_data):
    match post_json_data['type']:
        case "Photo":
            return handle_picture(post_json_data)
        case "Animated":
            return handle_video(post_json_data)
        case _:
            print(str(time.time()))
            print(post_json_data['type'])
            json_formatted_str = json.dumps(post_json_data, indent=2)
            with open(str(time.time()), "w") as f:
                f.write(json_formatted_str)
            return {}


def handle_picture(post_json_data):
    return_data = {}
    return_data['site'] = "9gag"
    return_data['id'] = post_json_data['id']
    return_data['url'] = post_json_data['url']
    return_data['text'] = post_json_data['title']
    return_data['spoiler'] = False
    if "image700" in post_json_data['images']:
        return_data['media'] = [
            [post_json_data['images']['image700']['url'], "photo"]]
        return_data['type'] = "media"
    elif "image460" in post_json_data['images']:
        return_data['media'] = [
            [post_json_data['images']['image460']['url'], "photo"]]
        return_data['type'] = "media"
    return return_data


def handle_video(post_json_data):
    return_data = {}
    return_data['site'] = "9gag"
    return_data['id'] = post_json_data['id']
    return_data['url'] = post_json_data['url']
    return_data['text'] = post_json_data['title']
    return_data['spoiler'] = False
    if "image700sv" in post_json_data['images']:
        video_type = "video"
        if post_json_data['images']['image700sv']['hasAudio'] == 0 and post_json_data['images']['image700sv']['duration'] <= 20:
            video_type = "gif"
        return_data['media'] = [
            [post_json_data['images']['image700sv']['url'], video_type]]
        return_data['type'] = "media"
    elif "image460sv" in post_json_data['images']:
        video_type = "video"
        if post_json_data['images']['image460sv']['hasAudio'] == 0 and post_json_data['images']['image460sv']['duration'] <= 20:
            video_type = "gif"
        return_data['media'] = [
            [post_json_data['images']['image460sv']['url'], video_type]]
        return_data['type'] = "media"
    return return_data
