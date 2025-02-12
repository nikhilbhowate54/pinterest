from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from pymongo import MongoClient
import gridfs

app = Flask(__name__)
CORS(app)

# MongoDB connection
mongo_client = MongoClient("mongodb+srv://raghavalawrence095:zktLJ8e0C0sJkUAM@cluster0.wgapa.mongodb.net/")
db = mongo_client['your_database_name']  # Replace with your database name
fs = gridfs.GridFS(db)  # Create a GridFS instance

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

    # Save video file to MongoDB using GridFS
    response = requests.get(video_download_url, stream=True)
    if response.status_code == 200:
        # Store video in GridFS
        fs.put(response.raw, filename=datetime.now().strftime("%d_%m_%H_%M_%S_") + ".mp4", content_type='video/mp4')
        return jsonify({'message': 'Video downloaded and saved to MongoDB.'}), 200
    else:
        return jsonify({'error': 'Failed to download video.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
