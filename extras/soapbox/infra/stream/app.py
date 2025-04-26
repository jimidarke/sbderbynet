import os
import subprocess
from flask import Flask, send_from_directory, render_template

app = Flask(__name__)
STREAM_DIR = 'stream'
RTSP_URL = 'rtsp://admin:all4theKids@192.168.100.20:554/21' # ptz camera 1920x1080
#RTSP_URL = 'rtsp://admin:all4theKids@192.168.100.20:554/11' # fixed camera 1920x1080

# Launch FFmpeg at startup
def start_ffmpeg():
    os.makedirs(STREAM_DIR, exist_ok=True)
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', RTSP_URL,
#        '-s', '1920x1080', 
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-tune', 'zerolatency',
        '-crf', '23',
        '-an',
        '-f', 'hls',
        '-hls_time', '4',
        '-hls_list_size', '5',
        '-hls_flags', 'delete_segments',
        f'{STREAM_DIR}/stream.m3u8'
    ]
    return subprocess.Popen(cmd)

# Serve the HLS files with correct MIME types
@app.route('/stream/<path:filename>')
def stream_files(filename):
    return send_from_directory(STREAM_DIR, filename)

# Optional: a browser viewer
@app.route('/')
def index():
    return render_template('player.html')

if __name__ == '__main__':
    start_ffmpeg()
    app.run(host='0.0.0.0', port=8081)
