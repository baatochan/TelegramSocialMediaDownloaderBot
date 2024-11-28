
import time
import traceback

import requests
from bs4 import BeautifulSoup
from getuseragent import UserAgent


def handle_url(link):
    user_agent = UserAgent().Random()
    headers = {'User-Agent': user_agent}
    try:
        link_parts = link.split("/")
        # link_parts[0] is https:, [1] is empty, [2] is demotywatory.pl, [4] is name of the post
        post_id = link_parts[3]

        if not post_id.isdigit():
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Demotywatory.pl post id is not a number, it is: " +
                  post_id + " for link: " + link)
            return {}

        response = requests.get(link, headers=headers)
        soup = BeautifulSoup(response.content.decode(), 'html.parser')

        meme_content = soup.find("div", id="demot{}".format(post_id))

        if not meme_content:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Demotywatory.pl: Couldn't find meme content for link: " + link)
            return {}

        return parse_meme(meme_content, post_id)

    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print()
        return {}


def parse_meme(meme_content, id):
    return_data = {}
    return_data['site'] = "demotywatory"
    return_data['id'] = id
    return_data['url'] = "https://demotywatory.pl/{}".format(id)
    return_data['type'] = "media"
    return_data['spoiler'] = False

    if meme_content.find("div", class_="gallery"):
        # TODO: add support for galleries, prerequisites: add support for spliting posts
        # with more than 10 medias
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        print("Demotywatory.pl: galleries are not supported, link: " +
              return_data['url'])
        return {}

    if meme_content.find("video"):
        video_link = meme_content.find("video").find("source")["src"]
        return_data['media'] = [[video_link, "video"]]
        return_data['text'] = meme_content.find("h2").find("a").string

    elif meme_content.find("img"):
        image_link = meme_content.find("img")["src"]
        return_data['media'] = [[image_link, "photo"]]

    else:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        print("Demotywatory.pl: Couldn't find media content for post: " +
              return_data['url'])
        return {}

    return return_data
