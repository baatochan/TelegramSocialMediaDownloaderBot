"""Handler modules for different social media platforms."""

from .booru_handler import BooruHandler
from .demoty_handler import DemotyHandler
from .instagram_handler import InstagramHandler
from .ninegag_handler import NineGagHandler
from .tiktok_handler import TikTokHandler
from .twitter_handler import TwitterHandler
from .youtube_handler import YouTubeHandler

__all__ = [
    'BooruHandler',
    'DemotyHandler',
    'InstagramHandler',
    'NineGagHandler',
    'TikTokHandler',
    'TwitterHandler',
    'YouTubeHandler',
]
