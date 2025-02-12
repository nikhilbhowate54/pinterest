from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import os
import threading
import time

app = Flask(__name__)
CORS(app)

# Directory to store downloaded videos
VIDEO_STORAGE_DIR = 'videos'

# Ensure the video storage directory exists
os.makedirs(VIDEO_STORAGE_DIR, exist_ok=True)

# Function to fetch video URL from Pinterest
def fetch_video_url(page_url):
    if "pinterest.com/pin/" not in page_url and "https://pin.it/" not in page_url:
        return None

    if "https://pin.it/" in page_url:  # Shortened pin URL check
        t_body = requests.get(page_url)
        if t_body.status_code != 200:
            return None
        soup = BeautifulSoup(t_body.content, "html.parser")
        href_link = (soup.find("link", rel="alternate"))['href']
        match = re.search('url=(.*?)&', href_link)
        page_url = match.group(1)  # Update page URL

    body = requests.get(page_url)  # GET response from URL
    if body.status_code != 200:  # Check status code
        return None

    soup = BeautifulSoup(body.content, "html.parser")  # Parsing the content
    extract_video_tag = soup.find("video", class_="hwa kVc MIw L4E")

    if extract_video_tag is None:
        print("No video tag found on the page.")
        return None

    extract_url = extract_video_tag['src']
    # Converting m3u8 to V_720P's URL
    convert_url = extract_url.replace("hls", "720p").replace("m3u8", "mp4")
    return convert_url

@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    video_url = data.get('url')

    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400

    print("Fetching content from given URL...")
    video_download_url = fetch_video_url(video_url)

    if not video_download_url:
        return jsonify({'error': 'Invalid URL or unable to fetch video'}), 400

    print("Downloading file now!")

    # Download video file and save it to the local storage
    try:
        response = requests.get(video_download_url, stream=True)
        if response.status_code == 200:
            filename = os.path.join(VIDEO_STORAGE_DIR, datetime.now().strftime("%d_%m_%H_%M_%S_") + ".mp4")
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            print(f"Video downloaded and saved as: {filename}")
            return send_file(filename, as_attachment=True)  # Send the downloaded file
        else:
            return jsonify({'error': 'Failed to download video.'}), 500
    except Exception as e:
        print(f"Error downloading video: {e}")
        return jsonify({'error': 'An error occurred while downloading the video.'}), 500

def cleanup_old_videos():
    """Remove video files older than 5 minutes."""
    while True:
        # Define how old a video must be to be deleted (e.g., older than 5 minutes)
        minutes_to_keep = 5
        cutoff_time = datetime.now() - timedelta(minutes=minutes_to_keep)

        # Iterate through the video storage directory and delete old files
        for filename in os.listdir(VIDEO_STORAGE_DIR):
            file_path = os.path.join(VIDEO_STORAGE_DIR, filename)
            if os.path.isfile(file_path):
                file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_creation_time < cutoff_time:
                    os.remove(file_path)
                    print(f"Deleted old video file: {filename}")

        # Sleep for a specified interval before checking again (e.g., every minute)
        time.sleep(60)

# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_videos, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True)
