"""
BhashaBridge - AI Translation Server
Simple Flask app that runs on Render.com
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import os
import base64
import io
from datetime import datetime

# Create Flask app
app = Flask(__name__)
CORS(app)  # Allow requests from any website

# ============================================
# API KEYS - Set these in Render dashboard
# ============================================
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
EXOTEL_SID = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN", "")
EXOTEL_CALLER_ID = os.getenv("EXOTEL_CALLER_ID", "")

# ============================================
# SAVE DATA IN MEMORY (simple for now)
# ============================================
voices = {}      # user_id -> voice_id
sessions = {}    # call_id -> call_info

# ============================================
# WEB PAGE - What users see
# ============================================
WEB_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>BhashaBridge - AI Translation</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: white; }
        h1 { color: #e94560; text-align: center; }
        .box { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
        input, select, textarea, button { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: none; }
        button { background: #e94560; color: white; cursor: pointer; font-size: 16px; }
        button:hover { background: #ff6b6b; }
        .result { background: #0f3460; padding: 15px; border-radius: 5px; margin-top: 10px; }
        .green { color: #4ecca3; }
        .red { color: #e94560; }
    </style>
</head>
<body>
    <h1>🌉 BhashaBridge</h1>
    <p style="text-align:center">Speak any language. AI translates instantly.</p>

    <!-- VOICE CLONING -->
    <div class="box">
        <h2>🎙️ Step 1: Clone Your Voice</h2>
        <input type="text" id="uid" placeholder="Your Name" value="rajesh">
        <input type="file" id="audiofile" accept="audio/*">
        <button onclick="cloneVoice()">Clone My Voice</button>
        <div id="vresult"></div>
    </div>

    <!-- TRANSLATION -->
    <div class="box">
        <h2>💬 Step 2: Translate</h2>
        <select id="from">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="ta">Tamil</option>
            <option value="te">Telugu</option>
            <option value="bn">Bengali</option>
        </select>
        <span style="display:block;text-align:center">↓</span>
        <select id="to">
            <option value="hi">Hindi</option>
            <option value="en">English</option>
            <option value="ta">Tamil</option>
            <option value="te">Telugu</option>
            <option value="bn">Bengali</option>
        </select>
        <textarea id="text" placeholder="Type something..." rows="3"></textarea>
        <input type="text" id="target" placeholder="Friend's Name (for their voice)">
        <button onclick="translate()">Translate & Speak</button>
        <div id="tresult"></div>
        <audio id="player" controls style="width:100%;margin-top:10px;display:none"></audio>
    </div>

    <!-- PHONE CALL -->
    <div class="box">
        <h2>📞 Step 3: Call Someone</h2>
        <input type="tel" id="myphone" placeholder="Your Phone (+91...)">
        <input type="tel" id="friendphone" placeholder="Friend's Phone (+91...)">
        <button onclick="call()">Start Translation Call</button>
        <div id="cresult"></div>
    </div>

    <script>
        const API = window.location.origin;  // This server

        async function cloneVoice() {
            const uid = document.getElementById('uid').value;
            const file = document.getElementById('audiofile').files[0];
            const div = document.getElementById('vresult');
            
            if (!file) { div.innerHTML = '<p class="red">Please select audio file</p>'; return; }
            
            div.innerHTML = '<p>Cloning... please wait</p>';
            const form = new FormData();
            form.append('audio', file);
            form.append('user_id', uid);
            
            const res = await fetch(API + '/clone', {method: 'POST', body: form});
            const data = await res.json();
            
            if (data.success) div.innerHTML = '<p class="green">✅ Voice cloned! ID: ' + data.voice_id + '</p>';
            else div.innerHTML = '<p class="red">❌ Error: ' + (data.error || 'Failed') + '</p>';
        }

        async function translate() {
            const text = document.getElementById('text').value;
            const from = document.getElementById('from').value;
            const to = document.getElementById('to').value;
            const target = document.getElementById('target').value;
            const div = document.getElementById('tresult');
            const player = document.getElementById('player');
            
            if (!text) return;
            div.innerHTML = '<p>Translating...</p>';
            
            const res = await fetch(API + '/translate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: text, from_lang: from, to_lang: to, target_user: target})
            });
            const data = await res.json();
            
            if (data.success) {
                div.innerHTML = '<div class="result"><p>Original: ' + data.original + '</p><p class="green">Translation: ' + data.translated + '</p></div>';
                if (data.audio) {
                    player.src = 'data:audio/mp3;base64,' + data.audio;
                    player.style.display = 'block';
                    player.play();
                }
            } else {
                div.innerHTML = '<p class="red">Error: ' + (data.error || 'Failed') + '</p>';
            }
        }

        async function call() {
            const myphone = document.getElementById('myphone').value;
            const friendphone = document.getElementById('friendphone').value;
            const div = document.getElementById('cresult');
            
            if (!myphone || !friendphone) { div.innerHTML = '<p class="red">Enter both phone numbers</p>'; return; }
            
            div.innerHTML = '<p>Calling...</p>';
            const res = await fetch(API + '/call', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({from: myphone, to: friendphone})
            });
            const data = await res.json();
            
            if (data.success) div.innerHTML = '<p class="green">✅ Call started!</p>';
            else div.innerHTML = '<p class="red">❌ ' + (data.error || 'Failed') + '</p>';
        }
    </script>
</body>
</html>
"""

# ============================================
# SARVAM AI - Translates text
# ============================================
def translate_with_sarvam(text, from_lang, to_lang):
    """Send text to Sarvam AI and get translation"""
    try:
        response = requests.post(
            "https://api.sarvam.ai/v1/translate",
            headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
            json={
                "input": text,
                "source_language_code": from_lang,
                "target_language_code": to_lang,
                "mode": "formal",
                "model": "mayura:v1"
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("translated_text", text)
        return text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

# ============================================
# ELEVENLABS - Clones voice and speaks
# ============================================
def clone_with_elevenlabs(audio_bytes, name):
    """Clone voice from audio file"""
    try:
        response = requests.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            data={"name": name, "description": f"Voice of {name}", "labels": "{}"},
            files={"files": ("voice.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get("voice_id")
        return None
    except Exception as e:
        print(f"Voice clone error: {e}")
        return None

def speak_with_elevenlabs(text, voice_id):
    """Convert text to speech using cloned voice"""
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.content  # Audio bytes
        return None
    except Exception as e:
        print(f"Speech error: {e}")
        return None

# ============================================
# EXOTEL - Makes phone calls
# ============================================
def call_with_exotel(from_phone, to_phone):
    """Make phone call via Exotel"""
    try:
        # Format numbers
        for num in [from_phone, to_phone]:
            if not num.startswith("+"):
                num = "+91" + num.lstrip("0")
        
        url = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@api.in.exotel.com/v1/Accounts/{EXOTEL_SID}/Calls/connect.json"
        response = requests.post(url, data={
            "From": from_phone,
            "To": to_phone,
            "CallerId": EXOTEL_CALLER_ID,
            "CallType": "trans"
        }, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Call error: {e}")
        return False

# ============================================
# WEBSITE ROUTES
# ============================================

@app.route("/")
def homepage():
    """Show the web page"""
    return render_template_string(WEB_PAGE)

@app.route("/health")
def health():
    """Check if server is running"""
    return jsonify({"status": "ok", "service": "BhashaBridge"})

# ============================================
# API ROUTES
# ============================================

@app.route("/clone", methods=["POST"])
def clone_voice():
    """Clone user's voice from uploaded audio"""
    # Get uploaded file
    audio_file = request.files.get("audio")
    user_id = request.form.get("user_id", "")
    
    if not audio_file:
        return jsonify({"success": False, "error": "No audio file uploaded"})
    
    # Read audio bytes
    audio_bytes = audio_file.read()
    
    # Send to ElevenLabs
    voice_id = clone_with_elevenlabs(audio_bytes, user_id)
    
    if voice_id:
        voices[user_id] = voice_id  # Save for later
        return jsonify({"success": True, "voice_id": voice_id})
    else:
        return jsonify({"success": False, "error": "Voice cloning failed"})

@app.route("/translate", methods=["POST"])
def translate():
    """Translate text and optionally speak in cloned voice"""
    data = request.json
    text = data.get("text", "")
    from_lang = data.get("from_lang", "en")
    to_lang = data.get("to_lang", "hi")
    target_user = data.get("target_user", "")
    
    if not text:
        return jsonify({"success": False, "error": "No text provided"})
    
    # Translate
    translated = translate_with_sarvam(text, from_lang, to_lang)
    
    # Generate audio in target user's voice
    audio_base64 = None
    if target_user and target_user in voices:
        voice_id = voices[target_user]
        audio_bytes = speak_with_elevenlabs(translated, voice_id)
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode()
    
    return jsonify({
        "success": True,
        "original": text,
        "translated": translated,
        "audio": audio_base64
    })

@app.route("/call", methods=["POST"])
def make_call():
    """Start phone call between two numbers"""
    data = request.json
    from_phone = data.get("from", "")
    to_phone = data.get("to", "")
    
    if not from_phone or not to_phone:
        return jsonify({"success": False, "error": "Both phone numbers required"})
    
    # Make call
    success = call_with_exotel(from_phone, to_phone)
    
    if success:
        return jsonify({"success": True, "message": "Call initiated"})
    else:
        return jsonify({"success": False, "error": "Failed to make call"})

# ============================================
# START SERVER
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
