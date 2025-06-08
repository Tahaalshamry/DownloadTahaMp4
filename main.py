
from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import tempfile
import threading
from urllib.parse import urlparse

app = Flask(__name__)

# Store download progress
download_progress = {}

class ProgressHook:
    def __init__(self, video_id):
        self.video_id = video_id
    
    def __call__(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            download_progress[self.video_id] = {
                'status': 'downloading',
                'percent': percent,
                'speed': d.get('_speed_str', 'N/A')
            }
        elif d['status'] == 'finished':
            download_progress[self.video_id] = {
                'status': 'finished',
                'filename': d['filename']
            }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')
    
    if not video_url:
        return jsonify({'error': 'رابط الفيديو مطلوب'}), 400
    
    # Generate unique ID for this download
    video_id = str(hash(video_url))
    
    # Start download in background thread
    thread = threading.Thread(target=download_worker, args=(video_url, video_id))
    thread.start()
    
    return jsonify({'video_id': video_id, 'message': 'بدء التحميل...'})

@app.route('/progress/<video_id>')
def get_progress(video_id):
    progress = download_progress.get(video_id, {'status': 'unknown'})
    return jsonify(progress)

@app.route('/file/<video_id>')
def download_file(video_id):
    progress = download_progress.get(video_id)
    if progress and progress.get('status') == 'finished':
        filename = progress.get('filename')
        if filename and os.path.exists(filename):
            return send_file(filename, as_attachment=True)
    return jsonify({'error': 'الملف غير متوفر'}), 404

def download_worker(video_url, video_id):
    try:
        # Create downloads directory
        downloads_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(downloads_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [ProgressHook(video_id)],
        }
        
        # Initialize download progress
        download_progress[video_id] = {'status': 'starting'}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
    except Exception as e:
        download_progress[video_id] = {
            'status': 'error',
            'error': str(e)
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
