from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
from datetime import datetime
import os
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# MongoDB connection
mongo_client = MongoClient("mongodb+srv://raghavalawrence095:zktLJ8e0C0sJkUAM@cluster0.wgapa.mongodb.net/")
db = mongo_client['your_database_name']  # Replace with your database name
videos_collection = db['videos']  # Capped collection to store video metadata

# Download function
def download_file(url, filename):
    response = requests.get(url, stream=True)
    file_size = int(response.headers.get('Content-Length', 0))
    progress = tqdm(response.iter_content(1024), f'Downloading {filename}', total=file_size, unit='B', unit_scale=True, unit_divisor=1024)

    with open(filename, 'wb') as f:
        for data in progress.iterable:
            f.write(data)
            progress.update(len(data))

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

    filename = datetime.now().strftime("%d_%m_%H_%M_%S_") + ".mp4"
    print("Downloading file now!")
    download_file(video_download_url, filename)

    # Save video metadata to MongoDB
    video_data = {
        'url': video_download_url,
        'filename': filename,
        'downloaded_at': datetime.now()
    }
    videos_collection.insert_one(video_data)  # Insert video metadata into the capped collection

    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
