from instagrapi.exceptions import LoginRequired


def set_basic_settings(ig_client):
    ig_client.set_locale('en_US')
    ig_client.set_country('PL')
    ig_client.set_country_code(48)
    ig_client.set_timezone_offset(2 * 60 * 60)


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
        set_basic_settings(ig_client)
        ig_client.dump_settings("ig_session.json")


def handle_url(ig_client, link):
    media_id = ig_client.media_pk_from_url(link)
    api_response = ig_client.media_info(media_id).dict()
    return_data = {}
    return_data['site'] = "instagram"
    return_data['id'] = api_response['id']
    return_data['url'] = link
    return_data['text'] = prepare_description(api_response)
    return_data['author'] = prepare_author(api_response)
    return_data['spoiler'] = False
    match api_response['media_type']:
        case 1:  # photo
            return_data['media'] = [
                [api_response['thumbnail_url'].unicode_string(), "photo"]]
            return_data['type'] = "media"
            return return_data
        case 2:  # video
            return_data['media'] = [
                [api_response['video_url'].unicode_string(), "video"]]
            return_data['type'] = "media"
            return return_data
        case 8:  # album
            return_data['media'] = []
            for media in api_response['resources']:
                if media['media_type'] == 1:
                    return_data['media'].append(
                        [media['thumbnail_url'].unicode_string(), "photo"])
                elif media['media_type'] == 2:
                    return_data['media'].append(
                        [media['video_url'].unicode_string(), "video"])
                else:
                    print("This type of media (" +
                          media['media_type'] + ") is not supported.")
                    print(api_response)
            return_data['type'] = "media"
            return return_data
        case _:  # unknown
            print("This type of media (" +
                  api_response['media_type'] + ") is not supported.")
            print(api_response)
            return {}


def prepare_description(api_response):
    text = ""
    if api_response['caption_text'] is not None:
        text += api_response['caption_text']
    if api_response['accessibility_caption'] is not None:
        text += "\n" + api_response['accessibility_caption']
    return text


def prepare_author(api_response):
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
