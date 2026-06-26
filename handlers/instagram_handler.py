from instagrapi import Client
from instagrapi.exceptions import LoginRequired

from handlers.base import MediaHandler, PostData


class InstagramHandler(MediaHandler):
    def __init__(self, ig_client):
        self.ig_client = ig_client

    @staticmethod
    def set_basic_settings(ig_client):
        ig_client.set_locale('en_US')
        ig_client.set_country('PL')
        ig_client.set_country_code(48)
        ig_client.set_timezone_offset(2 * 60 * 60)

    @staticmethod
    def login_ig_user(ig_client, ig_config):
        try:
            session = ig_client.load_settings("ig_session.json")
        except FileNotFoundError:
            session = None
        except Exception as e:
            print("Couldn't load session file: ", str(e))
            session = None

        login_via_session = False
        login_via_pw = False
        new_session_created = False

        if session is not None:
            try:
                ig_client.set_settings(session)
                ig_client.login(username=ig_config['username'],
                                password=ig_config['password'])

                # check if session is valid
                try:
                    ig_client.get_timeline_feed()
                except LoginRequired:
                    print("Session is invalid, need to login via username and password")

                    old_session = ig_client.get_settings()
                    new_session_created = True

                    # use the same device uuids across logins
                    ig_client.set_settings({})
                    ig_client.set_uuids(old_session["uuids"])

                    ig_client.login(username=ig_config['username'],
                                    password=ig_config['password'])

                login_via_session = True
            except Exception as e:
                print("Couldn't login user using session information: ", str(e))

        if not login_via_session:
            try:
                print("Attempting to login via username and password. username: " +
                      ig_config['username'])
                if ig_client.login(username=ig_config['username'], password=ig_config['password']):
                    login_via_pw = True
                    new_session_created = True
            except Exception as e:
                print("Couldn't login user using username and password: ", str(e))

        if not login_via_pw and not login_via_session:
            raise Exception(
                "Couldn't login ig user with either password or session")

        if new_session_created:
            InstagramHandler.set_basic_settings(ig_client)
            ig_client.dump_settings("ig_session.json")

    @classmethod
    def create_from_config(cls, ig_config):
        ig_client = Client()

        if ig_config.getboolean('do_login'):
            cls.login_ig_user(ig_client, ig_config)
            print("Started an ig client with an account with following settings:")
        else:
            cls.set_basic_settings(ig_client)
            print("Started an ig client without an account with following settings:")

        print(ig_client.get_settings())
        return cls(ig_client)

    def handle(self, link: str) -> PostData | None:
        try:
            media_id = self.ig_client.media_pk_from_url(link)
            api_response = self.ig_client.media_info(media_id).dict()

            post_data = PostData(
                site="instagram",
                post_type="media",
                post_id=api_response['id'],
                url=link,
                text=self._prepare_description(api_response),
                author=self._prepare_author(api_response),
                spoiler=False,
            )

            return self._check_media(post_data, api_response)
        except Exception as e:
            print("Couldn't get instagram post from url: " + link)
            print(str(e))
            return None

    def _check_media(self, post_data, api_response):
        match api_response['media_type']:
            case 1:  # photo
                post_data.media = [
                    [api_response['thumbnail_url'].unicode_string(), "photo"]]
                return post_data
            case 2:  # video
                post_data.media = [
                    [api_response['video_url'].unicode_string(), "video"]]
                return post_data
            case 8:  # album
                for media in api_response['resources']:
                    if media['media_type'] == 1:
                        post_data.media.append(
                            [media['thumbnail_url'].unicode_string(), "photo"])
                    elif media['media_type'] == 2:
                        post_data.media.append(
                            [media['video_url'].unicode_string(), "video"])
                    else:
                        print("This type of media (" +
                              media['media_type'] + ") is not supported.")
                        print(api_response)
                return post_data
            case _:  # unknown
                print("This type of media (" +
                      api_response['media_type'] + ") is not supported.")
                print(api_response)
                return None

    def _prepare_description(self, api_response):
        text = ""
        if api_response['caption_text'] is not None:
            text += api_response['caption_text']
        if api_response['accessibility_caption'] is not None:
            text += "\n" + api_response['accessibility_caption']
        return text

    def _prepare_author(self, api_response):
        author = ""
        is_fullname = api_response['user']['full_name'] is not None
        is_username = api_response['user']['username'] is not None

        if is_fullname:
            author += api_response['user']['full_name']
        if is_fullname and is_username:
            author += " ("
        if is_username:
            author += "@" + api_response['user']['username']
        if is_fullname and is_username:
            author += ")"

        return author
