
import re
import time
import traceback
import yt_dlp_wrapper


def handle_url(link):
    clean_link = clean_up_url(link)
    try:
        [output_filename, info_dict] = yt_dlp_wrapper.download(clean_link)
        return prepare_metadata(output_filename, info_dict)
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print("Couldn't get video from url: " + link)
        print()
        return {}


def clean_up_url(link):
    link = re.sub(r"si=([\w\-_]*)", "", link)  # Remove si parameter
    link = re.sub(r"[?&]+$", "", link)  # Remove trailing "?" or "&"
    link = re.sub(r"&+", "&", link)  # Remove multiple "&"
    link = re.sub(r"\?&", "?", link)  # Replace ?& with ?
    return link


def prepare_metadata(output_filename, info_dict):
    return_data = {}
    return_data['site'] = "youtube"
    return_data['id'] = info_dict['id']
    return_data['url'] = info_dict['original_url']

    return_data['author'] = info_dict['uploader'] + \
        " (" + info_dict['uploader_id'] + ")"

    return_data['text'] = info_dict['fulltitle']
    return_data['spoiler'] = False
    return_data['media'] = [[output_filename, "video_file"]]
    return_data['type'] = "media"
    return return_data
