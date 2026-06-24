
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
        domain_index = [i for i, part in enumerate(
            link_parts) if part.endswith('demotywatory.pl')][0]
        # post id is the next part after the domain
        post_id = link_parts[domain_index + 1]

        if not post_id.isdigit():
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Demotywatory.pl post id is not a number, it is: " +
                  post_id + " for link: " + link)
            return {}

        # recreating the link because the mobile site has a different layout
        link_to_download = "https://demotywatory.pl/{}".format(post_id)

        response = requests.get(link_to_download, headers=headers)
        soup = BeautifulSoup(response.content.decode(), 'html.parser')

        meme_content = soup.find("div", id="demot{}".format(post_id))

        if not meme_content:
            print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
            print("Demotywatory.pl: Couldn't find meme content for link: " + link)
            return {}

        site_head = soup.find("head")

        return parse_meme(meme_content, site_head, post_id)

    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print()
        return {}


def parse_meme(meme_content, head, id):
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
        return_data['text'] = get_description_for_video_post(head)

    elif meme_content.find("img"):
        image_link = meme_content.find("img")["src"]
        return_data['media'] = [[image_link, "photo"]]

    else:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        print("Demotywatory.pl: Couldn't find media content for post: " +
              return_data['url'])
        return {}

    if meme_content.find("div", class_="youtube"):
        yt_link = meme_content.find(
            "div", class_="youtube").find("iframe")["src"]
        yt_link = yt_link.split("?")[0]
        yt_id = yt_link.split("/")[-1]
        if not "text" in return_data:
            return_data['text'] = ""
        return_data['text'] = return_data['text'] + "\n" + \
            "Ten demotywator zawiera link do yt: https://youtu.be/" + yt_id

    return return_data


def get_description_for_video_post(head):
    PLACEHOLDER = "Demotywatory to śmieszne, ironiczne i poważne plakaty - obrazki o życiu, miłości, dzieciństwie i dorastaniu, animowane gify, śmieszne i ciekawe filmy. Aktualności i przegląd internetu, cytaty."

    title = head.find("meta", property="og:title")["content"]
    description = head.find("meta", property="og:description")["content"]

    if title == PLACEHOLDER:
        title = None
    if description == PLACEHOLDER:
        description = None

    if title and description:
        return title + "\n" + description
    elif title:
        return title
    elif description:
        return description
    else:
        return ""
