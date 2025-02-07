import json
import time
import traceback

import requests

import file_converter
import file_downloader

CONVERT_WEBM_VIDEO = False


def handle_url(link):
    headers = {'User-Agent': "Telegram Social Media Downloader Bot"}

    link_parts = link.split('/')

    # look for full site name, returns list of indexes
    site_idx = [i for i, item in enumerate(
        link_parts) if item.endswith('booru.org')]
    # the first index should point to the site name
    site_id = site_idx[0] if site_idx else None
    if not site_id:
        print("Couldn't get image from url (can't find the domain): " + link)
        print()
        return {}
    domain = link_parts[site_id]

    if link_parts[site_id + 1] == "images":
        post_number = link_parts[site_id + 2]
    else:
        post_number = link_parts[site_id + 1]

    if not post_number.isdigit():
        print("Couldn't get image from url (post number is not a number): " + link)
        print()
        return {}

    try:
        response = requests.get(
            "https://" + domain + "/api/v1/json/images/" + post_number, headers=headers)
        if response.status_code == 200:
            result = json.loads(response.text)
            return handle_image(result['image'], domain)
        else:
            print("Couldn't get image from url (code=" +
                  str(response.status_code) + "): " + link)
            print()
            return {}
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print("Couldn't get image from url: " + link)
        print()
        return {}


def handle_image(booru_image, domain):
    return_data = {}
    return_data['site'] = "booru"
    return_data['id'] = booru_image['id']

    author = check_if_author_known(booru_image['tags'])
    if author:
        return_data['author'] = author

    return_data['text'] = booru_image['description']
    return_data['url'] = "https://" + domain + "/" + str(booru_image['id'])

    return_data['type'] = "media"

    match booru_image['format']:
        case "jpg" | "jpeg" | "png" | "svg":
            # to be changed when booru api handles svg better
            # (currently only low quality png is returned)
            # height + width > 8000 is safe margin because tg api has a limit of 10k
            # but some images under 10k where rejected
            if booru_image['height'] + booru_image['width'] > 8000:
                return_data['media'] = [
                    [booru_image['representations']['large'], "photo"]]
            else:
                return_data['media'] = [
                    [booru_image['representations']['full'], "photo"]]
        case "gif":
            return_data['media'] = [
                [booru_image['representations']['full'], "gif"]]
        case "webm":
            return_data = handle_video(booru_image, return_data)
        case _:
            return_data['type'] = "text"
            return_data['text'] = "Unknown image format: " + \
                booru_image['format'] + "\n" + return_data['text']

    return_data['spoiler'] = booru_image['spoilered']

    return return_data


def check_if_author_known(tags):
    list_of_authors = []
    for tag in tags:
        if tag.startswith("artist:"):
            list_of_authors.append(tag[7:])
    if not list_of_authors:
        return None
    return ', '.join(list_of_authors)


def handle_video(booru_image, return_data):
    if CONVERT_WEBM_VIDEO:
        webm_filename = file_downloader.download_video(url=booru_image['representations']['full'],
                                                       site="booru",
                                                       id=str(booru_image['id']))

        converted_filename = file_converter.convert_webm_to_mp4(webm_filename)

        if converted_filename:
            return_data['media'] = [[converted_filename, "video_file"]]
        else:
            print("Couldn't convert webm to mp4: " + webm_filename)
            return_data['media'] = [
                [booru_image['representations']['full'], "video"]]
    else:
        return_data['media'] = [
            [booru_image['representations']['full'], "video"]]

    return return_data
