from enum import Enum
import ffmpeg
import os
import yt_dlp


class CompressionLevel(Enum):
    NO_RESIZE = 0
    RESIZE_480 = 480
    RESIZE_360 = 360


ydl_options = {
    "format": "bestvideo[height<=720][width>720][vcodec^=avc][ext=mp4]+bestaudio/"
              "bestvideo[width<=720][vcodec^=avc][ext=mp4]+bestaudio/"
              "best[height<=720][width>720]/"
              "best[width<=720]",
    "merge_output_format": "mp4",
    "outtmpl": "temp/yt-dlp/%(webpage_url_domain)s-%(id)s.%(ext)s",
}


compression_scenarios = [
    {
        "name": "hq",
        "size_threshold": 85 * 1000 * 1000,
        "resolution_resize": CompressionLevel.NO_RESIZE,
    },
    {
        "name": "mq",
        "size_threshold": 175 * 1000 * 1000,
        "resolution_resize": CompressionLevel.RESIZE_480,
    },
    {
        "name": "lq",
        "size_threshold": 500 * 1000 * 1000,
        "resolution_resize": CompressionLevel.RESIZE_360,
    },
]


def download(link):
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        vid_filename = ydl.prepare_filename(info_dict)
        size = os.path.getsize(vid_filename)
        if info_dict['vcodec'].startswith("vp09") or size > 50 * 1000 * 1000:
            is_vertical = info_dict['height'] > info_dict['width']
            vid_filename = compress_video(vid_filename, size, is_vertical)
        return vid_filename, info_dict


def compress_video(video_path, original_size, is_vertical=False):
    for scenario in compression_scenarios:
        if original_size < scenario["size_threshold"]:
            compressed_video_path = video_path.replace(
                ".mp4", f"-compressed-{scenario['name']}.mp4")
            if not os.path.exists(compressed_video_path):
                if scenario["resolution_resize"] == CompressionLevel.NO_RESIZE:
                    run_compression(video_path, compressed_video_path)
                else:
                    max_size = scenario['resolution_resize'].value
                    scale = f"scale={max_size}:-2" if is_vertical else f"scale=-2:{max_size}"
                    run_compression_with_resizing(
                        video_path, compressed_video_path, scale)
            compressed_size = os.path.getsize(compressed_video_path)
            if compressed_size < 50 * 1000 * 1000:
                return compressed_video_path

    if original_size < 50 * 1000 * 1000:
        # fallback to original video if compression fails
        return video_path

    raise Exception("Video is too large to compress")


def run_compression(video_path, output_file):
    ffmpeg\
        .input(video_path)\
        .output(output_file,
                vcodec="libx264",
                crf=28,
                preset="slow",
                acodec="aac",
                audio_bitrate="128k")\
        .overwrite_output()\
        .run()


def run_compression_with_resizing(video_path, output_file, scale):
    ffmpeg\
        .input(video_path)\
        .output(output_file,
                vcodec="libx264",
                crf=28,
                preset="slow",
                acodec="aac",
                audio_bitrate="128k",
                vf=scale)\
        .overwrite_output()\
        .run()
