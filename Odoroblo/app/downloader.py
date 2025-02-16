import yt_dlp
import os
import subprocess

async def get_file_size(url: str, platform: str):
    ydl_opts = {
        'quiet': True,
    }

    if platform == "youtube" or platform == "soundcloud":
        ydl_opts['format'] = 'bestaudio/best'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        file_size = info_dict.get("filesize")
        if not file_size:
            file_size = 0  # Якщо розмір не визначено, повертаємо 0

    return file_size

async def download_audio_from_youtube(video_url: str):
    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        file_path = ydl.prepare_filename(info_dict).replace(".webm", ".mp3").replace(".m4a", ".mp3")

    return file_path

async def download_audio_from_soundcloud(track_url: str):
    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(track_url, download=True)
        file_path = ydl.prepare_filename(info_dict).replace(".webm", ".mp3").replace(".m4a", ".mp3")

    return file_path

async def download_video_from_tiktok(video_url: str):
    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
    }

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        file_path = ydl.prepare_filename(info_dict)

    return file_path

async def download_audio_from_tiktok_video(video_url: str):
    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
    }

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        video_file_path = ydl.prepare_filename(info_dict)
    
    # Витягування аудіо з відео
    audio_file_path = video_file_path.replace(".mp4", ".mp3").replace(".webm", ".mp3")

    # Використовуємо FFmpeg для конвертації відео в аудіо
    command = [
        'ffmpeg', '-i', video_file_path, '-vn', '-acodec', 'libmp3lame', '-ab', '192k', audio_file_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Видалення відеофайлу після конвертації
    os.remove(video_file_path)

    return audio_file_path

async def download_video_from_instagram_reels(video_url: str):
    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
    }

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        file_path = ydl.prepare_filename(info_dict)

    return file_path

async def download_audio_from_instagram_reels_video(video_url: str):
    output_template = "downloads/%(title)s.%(ext)s"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
    }

    if not os.path.exists("downloads"):
        os.makedirs("downloads")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        video_file_path = ydl.prepare_filename(info_dict)
    
    # Витягування аудіо з відео
    audio_file_path = video_file_path.replace(".mp4", ".mp3").replace(".webm", ".mp3")

    # Використовуємо FFmpeg для конвертації відео в аудіо
    command = [
        'ffmpeg', '-i', video_file_path, '-vn', '-acodec', 'libmp3lame', '-ab', '192k', audio_file_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Видалення відеофайлу після конвертації
    os.remove(video_file_path)

    return audio_file_path
