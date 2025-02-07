import time
import traceback


def handle_url(reddit_client, link):
    try:
        submission = reddit_client.submission(url=link)
    except Exception as e:
        print(time.strftime("%d.%m.%Y %H:%M:%S", time.localtime()))
        traceback.print_exception(type(e), e, e.__traceback__)
        print("Couldn't get reddit post from url: " + link)
        print()
        return {}
