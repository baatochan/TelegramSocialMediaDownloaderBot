# TelegramSocialMediaDownloaderBot

A private Telegram bot for downloading and reposting content from various social media platforms, including Instagram, TikTok, 9gag, Twitter, Mastodon, booru-based imageboards, and demotywatory.pl. The bot is designed for personal/group use and supports media-rich posts, spoiler handling, and fallback mechanisms for unsupported or problematic links.

## Features

- **Supported Platforms:**  
  - Instagram  
  - TikTok  
  - 9gag  (Via Selenium or request)
  - Twitter (via FxTwitter API)  
  - Mastodon (auto-detection for any instance)  
  - Booru imageboards (e.g., derpibooru.org)  
  - Demotywatory.pl

- **Media Handling:**  
  - Downloads and sends photos, videos, GIFs, and albums  
  - Handles NSFW/spoiler flags for booru images  
  - Converts webm to mp4 for broader compatibility (optional)  
  - Handles Twitter polls and community notes

- **Telegram Integration:**  
  - Restricts usage to allowed users and chats  
  - Replies with media or fallback links  
  - Handles long captions and multi-media posts  
  - Deletes handled messages for chat cleanliness

- **Fallbacks:**  
  - Uses alternate services (e.g., ddinstagram, tfxktok) if native download fails  
  - Mastodon auto-detection for unknown domains

- **Configuration:**  
  - All settings via `config.txt` (see `config.default.txt` for template)  
  - Supports session-based or password-based Instagram login  
  - Optional Selenium usage for 9gag scraping

## Installation

```sh
git clone https://github.com/baatochan/TelegramSocialMediaDownloaderBot
cd TelegramSocialMediaDownloaderBot
pip install -r requirements.txt
cp config.default.txt config.txt
vim config.txt  # Edit your Telegram token and allowed users/chats
```

### Docker

A [Dockerfile](Dockerfile) is provided for containerized deployment:

```sh
docker build -t tg-social-media-bot .
docker run -v $(pwd)/logs:/app/logs tg-social-media-bot
```

## Usage

1. **Start the bot:**  
   Run `python bot.py` or use Docker as above.

2. **Send a supported link:**  
   - Paste a link from Instagram, TikTok, 9gag, Twitter, Mastodon, booru, or demotywatory.pl to the bot in Telegram.
   - The bot will download and send the media, handling spoilers and long captions as needed.

3. **Special commands:**  
   - `/start` or `/help` — Show welcome/help message  
   - `>>123456` — Fetch booru post by ID  
   - `UseInstafix = True/False` — Toggle Instagram fallback (admin only)

## Configuration

Edit `config.txt` (see `config.default.txt` for all options):

- **Telegram:**  
  - `token` — Your bot token from @BotFather  
  - `allowed_users` — List of Telegram user IDs  
  - `allowed_chats` — List of allowed group IDs  
  - `owner_username` — Your Telegram username

- **Instagram:**  
  - `do_login` — Use session or password login  
  - `username`, `password` — Instagram credentials

- **9gag:**  
  - `use_selenium` — Use Selenium for scraping (set to `False` to use requests only)

## Requirements

- Python 3.10+
- See [`requirements.txt`](requirements.txt) for Python dependencies
- For 9gag scraping with Selenium: Firefox and geckodriver
- **Optional:** [FFmpeg](https://ffmpeg.org/) — required for media conversion (e.g., webm to mp4)

If you want the bot to convert videos (such as webm to mp4), make sure `ffmpeg` is installed and available in your system `PATH`.

## License

[GNU Lesser General Public License v2.1](LICENSE)

---

**Disclaimer:**  
This bot is intended for personal/private use. Respect the terms of service of the platforms you interact with.