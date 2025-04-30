import ffmpeg
import os
import yt_dlp

ydl_opt = {
    "format": "bestvideo[height<=1080][width>1080][vcodec^=avc][ext=mp4]+bestaudio/"
              "bestvideo[width<=1080][vcodec^=avc][ext=mp4]+bestaudio/"
              "best[height<=1080][width>1080]/"
              "best[width<=1080]",
    "merge_output_format": "mp4",
    "outtmpl": "temp/yt-dlp/%(webpage_url_domain)s-%(id)s.%(ext)s",
}


def download(link):
    with yt_dlp.YoutubeDL(ydl_opt) as ydl:
        info_dict = ydl.extract_info(link, download=True)
        vid_filename = ydl.prepare_filename(info_dict)
        size = os.path.getsize(vid_filename)
        if info_dict['vcodec'].startswith("vp09") or size > 50 * 1000 * 1000:
            is_vertical = info_dict['height'] > info_dict['width']
            vid_filename = compress_video(vid_filename, size, is_vertical)
        return vid_filename, info_dict


def compress_video(video_path, original_size, is_vertical=False):
    if original_size < 75 * 1000 * 1000:
        compressed_video_path = video_path.replace(
            ".mp4", "-compressed-high.mp4")
        if not os.path.exists(compressed_video_path):
            compress_video_hq(video_path, compressed_video_path)
        compressed_size = os.path.getsize(compressed_video_path)
        if compressed_size < 50 * 1000 * 1000:
            return compressed_video_path

    if original_size < 125 * 1000 * 1000:
        compressed_video_path = video_path.replace(
            ".mp4", "-compressed-medium.mp4")
        if not os.path.exists(compressed_video_path):
            compress_video_mq(video_path, compressed_video_path, is_vertical)
        compressed_size = os.path.getsize(compressed_video_path)
        if compressed_size < 50 * 1000 * 1000:
            return compressed_video_path

    compressed_video_path = video_path.replace(
        ".mp4", "-compressed-low.mp4")
    if not os.path.exists(compressed_video_path):
        compress_video_lq(video_path, compressed_video_path, is_vertical)
    compressed_size = os.path.getsize(compressed_video_path)
    if compressed_size < 50 * 1000 * 1000:
        return compressed_video_path

    if original_size < 50 * 1000 * 1000:
        # fallback to original video if compression fails
        return video_path

    raise Exception("Video is too large to compress")


def compress_video_hq(video_path, output_file):
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


def compress_video_mq(video_path, output_file, is_vertical=False):
    scale = "scale=720:-2" if is_vertical else "scale=-2:720"
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


def compress_video_lq(video_path, output_file, is_vertical=False):
    scale = "scale=480:-2" if is_vertical else "scale=-2:480"
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
