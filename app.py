from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.fx.all import resize
import os
import glob
import random
import string
import ffmpeg
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

executor = ThreadPoolExecutor(max_workers=4)

def id_generator(size=24, chars=string.digits + string.ascii_letters):
    return ''.join(random.choice(chars) for _ in range(size))

UPLOAD_FOLDER = 'uploads'
VIDEO_FOLDER = 'static/videos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['VIDEO_FOLDER'] = VIDEO_FOLDER

# Ensure the upload and video directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)
# Define your conversion functions to be compatible with async
def convert_to_high_quality_sync(input_path, output_path):
    with VideoFileClip(input_path) as video:
        video = resize(video, height=1080)  # 1080p
        video.write_videofile(output_path, codec='libx264', bitrate='5000k', audio_bitrate="192k")

def convert_to_med_quality_sync(input_path, output_path):
    with VideoFileClip(input_path) as video:
        video = resize(video, height=720)  # 720p
        video.write_videofile(output_path, codec='libx264', bitrate='2500k', audio_bitrate="128k", fps=30)

def convert_to_low_quality_sync(input_path, output_path):
    with VideoFileClip(input_path) as video:
        video = resize(video, height=480)  # 480p
        video.write_videofile(output_path, codec='libx264', bitrate='100k', audio_bitrate="64k", fps=30)

def convert_to_very_low_quality_sync(input_path, output_path):
    with VideoFileClip(input_path) as video:
        video = resize(video, height=240)  # 240p
        video.write_videofile(output_path, codec='libx264', bitrate='30k', audio_bitrate="1k", fps=30)

# Wrap synchronous functions to be run asynchronously
async def convert_to_high_quality(input_path, output_path):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, convert_to_high_quality_sync, input_path, output_path)

async def convert_to_med_quality(input_path, output_path):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, convert_to_med_quality_sync, input_path, output_path)

async def convert_to_low_quality(input_path, output_path):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, convert_to_low_quality_sync, input_path, output_path)

async def convert_to_very_low_quality(input_path, output_path):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, convert_to_very_low_quality_sync, input_path, output_path)


@app.route('/')
def index():
    v_id = request.args.get("vid")
    req_file = Path(f"static/videos/{v_id}.mp4")
    if req_file.is_file():
        return render_template('player.html', v_id=f"{v_id}.mp4")
    else:
        return render_template('deadplayer.html')

@app.route('/uploader')
def uploader():
    return render_template("uploader.html")

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return 'No video part', 400

    file = request.files['video']
    if file.filename == '':
        return 'No selected file', 400

    if file:

        vid = id_generator()
        filename = f"{vid}.mp4"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        high_quality_path = os.path.join(app.config['VIDEO_FOLDER'], filename)
        med_quality_path = os.path.join(app.config['VIDEO_FOLDER'], f'med_{filename}')
        low_quality_path = os.path.join(app.config['VIDEO_FOLDER'], f'low_{filename}')
        very_low_quality_path = os.path.join(app.config['VIDEO_FOLDER'], f'very_low_{filename}')

        async def video_process_task():
            await asyncio.gather(
                convert_to_high_quality(file_path, high_quality_path),
                convert_to_med_quality(file_path, med_quality_path),
                convert_to_low_quality(file_path, low_quality_path),
                convert_to_very_low_quality(file_path, very_low_quality_path)
            )

        def run_async_task():
            asyncio.run(video_process_task())

        executor.submit(run_async_task)
        # Move original video to video folder


        return redirect(url_for('index', vid=vid))

@app.route('/videos/<filename>')
def get_video(filename):
    return send_from_directory(app.config['VIDEO_FOLDER'], filename)

@app.route('/video_paget')
def video_paths():
    request.args.get("video")
    videos = [f for f in os.listdir(app.config['VIDEO_FOLDER']) if os.path.isfile(os.path.join(app.config['VIDEO_FOLDER'], f))]
    return jsonify(videos)

if __name__ == '__main__':
    app.run(debug=True)
