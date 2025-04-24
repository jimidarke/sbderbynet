'''
Manages the RTSP camera feeds and such for displaying camera streams in the UI.

'''

from flask import Flask, render_template

app = Flask(__name__, static_url_path='/var/lib/infra/server/camstream/static')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
