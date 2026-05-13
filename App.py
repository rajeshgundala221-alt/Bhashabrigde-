"""
BhashaBridge - AI Translation Server
Flask + SQLite + Razorpay + Google Sign-In (Firebase)
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import requests
import os
import base64
import io
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================
# API KEYS - Set these in Render dashboard
# ============================================
SARVAM_API_KEY        = os.getenv("SARVAM_API_KEY", "")
ELEVENLABS_API_KEY    = os.getenv("ELEVENLABS_API_KEY", "")
EXOTEL_SID            = os.getenv("EXOTEL_SID", "")
EXOTEL_API_KEY        = os.getenv("EXOTEL_API_KEY", "")
EXOTEL_API_TOKEN      = os.getenv("EXOTEL_API_TOKEN", "")
EXOTEL_CALLER_ID      = os.getenv("EXOTEL_CALLER_ID", "")
RAZORPAY_KEY_ID       = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET   = os.getenv("RAZORPAY_KEY_SECRET", "")

# Firebase config - Set these in Render dashboard too
FIREBASE_API_KEY          = os.getenv("FIREBASE_API_KEY", "")
FIREBASE_AUTH_DOMAIN      = os.getenv("FIREBASE_AUTH_DOMAIN", "")
FIREBASE_PROJECT_ID       = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_APP_ID           = os.getenv("FIREBASE_APP_ID", "")

# ============================================
# SQLITE DATABASE
# ============================================
DB_PATH = "/tmp/bashabridge.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE,
            name TEXT,
            email TEXT,
            voice_id TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_phone TEXT,
            to_phone TEXT,
            status TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            order_id TEXT UNIQUE,
            amount INTEGER,
            status TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_user(uid, name, email):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (uid, name, email, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(uid) DO UPDATE SET name=excluded.name, email=excluded.email
        """, (uid, name, email, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB save user error: {e}")

def save_voice(uid, voice_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE users SET voice_id=? WHERE uid=?", (voice_id, uid))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB save voice error: {e}")

def get_voice_by_uid(uid):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT voice_id FROM users WHERE uid=?", (uid,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"DB get voice error: {e}")
    return None

def get_voice_by_name(name):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT voice_id FROM users WHERE name=?", (name,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f"DB get voice error: {e}")
    return None

def log_call(from_phone, to_phone, status):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO calls (from_phone, to_phone, status, created_at)
            VALUES (?, ?, ?, ?)
        """, (from_phone, to_phone, status, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB log error: {e}")

def save_payment(user_id, order_id, amount, status):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO payments (user_id, order_id, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, order_id, amount, status, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB payment error: {e}")

def update_payment_status(order_id, status):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE payments SET status=? WHERE order_id=?", (status, order_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB update error: {e}")

def is_user_paid(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM payments WHERE user_id=? AND status='paid'", (user_id,))
        row = c.fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        print(f"DB paid check error: {e}")
    return False

# ============================================
# WEB PAGE
# ============================================
WEB_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>BhashaBridge - AI Translation</title>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.7.0/firebase-auth-compat.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: white; }
        h1 { color: #e94560; text-align: center; }
        .box { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
        input, select, textarea, button { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: none; }
        button { background: #e94560; color: white; cursor: pointer; font-size: 16px; }
        button:hover { background: #ff6b6b; }
        .pay-btn { background: #4ecca3; color: #1a1a2e; font-weight: bold; }
        .google-btn { background: white; color: #333; display: flex; align-items: center; justify-content: center; gap: 10px; font-weight: bold; }
        .result { background: #0f3460; padding: 15px; border-radius: 5px; margin-top: 10px; }
        .green { color: #4ecca3; }
        .red { color: #e94560; }
        .yellow { color: #ffd700; }
        #app { display: none; }
        #login-screen { display: block; }
        .user-bar { background: #0f3460; padding: 10px 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .logout-btn { background: transparent; border: 1px solid #e94560; color: #e94560; width: auto; padding: 5px 12px; font-size: 13px; }
    </style>
</head>
<body>

    <!-- LOGIN SCREEN -->
    <div id="login-screen">
        <h1>🌉 BhashaBridge</h1>
        <p style="text-align:center">Speak any language. AI translates instantly.</p>
        <div class="box" style="text-align:center">
            <h2>Welcome</h2>
            <p style="color:#aaa">Sign in to continue</p>
            <button class="google-btn" onclick="signInWithGoogle()">
                <img src="https://www.google.com/favicon.ico" width="20"> Sign in with Google
            </button>
            <div id="login-error" style="margin-top:10px"></div>
        </div>
    </div>

    <!-- MAIN APP (shown after login) -->
    <div id="app">
        <h1>🌉 BhashaBridge</h1>

        <!-- USER BAR -->
        <div class="user-bar">
            <span id="user-name">👤 Loading...</span>
            <button class="logout-btn" onclick="logout()">Logout</button>
        </div>

        <!-- PAYMENT -->
        <div class="box">
            <h2>💳 Subscribe - ₹99/month</h2>
            <div id="access-status"></div>
            <button class="pay-btn" onclick="startPayment()">Pay ₹99 & Activate</button>
            <div id="presult"></div>
        </div>

        <!-- VOICE CLONING -->
        <div class="box">
            <h2>🎙️ Step 1: Clone Your Voice</h2>
            <input type="file" id="audiofile" accept="audio/*">
            <button onclick="cloneVoice()">Clone My Voice</button>
            <div id="vresult"></div>
        </div>

        <!-- TRANSLATION -->
        <div class="box">
            <h2>💬 Step 2: Translate</h2>
            <select id="from">
                <option value="en-IN">English</option>
                <option value="hi-IN">Hindi</option>
                <option value="ta-IN">Tamil</option>
                <option value="te-IN">Telugu</option>
                <option value="bn-IN">Bengali</option>
                <option value="kn-IN">Kannada</option>
                <option value="ml-IN">Malayalam</option>
            </select>
            <span style="display:block;text-align:center;padding:5px">↓</span>
            <select id="to">
                <option value="hi-IN">Hindi</option>
                <option value="en-IN">English</option>
                <option value="ta-IN">Tamil</option>
                <option value="te-IN">Telugu</option>
                <option value="bn-IN">Bengali</option>
                <option value="kn-IN">Kannada</option>
                <option value="ml-IN">Malayalam</option>
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
    </div>

    <script>
        // ============================================
        // FIREBASE CONFIG - injected from server
        // ============================================
        const firebaseConfig = {
            apiKey: "{{ firebase_api_key }}",
            authDomain: "{{ firebase_auth_domain }}",
            projectId: "{{ firebase_project_id }}",
            appId: "{{ firebase_app_id }}"
        };
        firebase.initializeApp(firebaseConfig);
        const auth = firebase.auth();

        const API = window.location.origin;
        let currentUser = null;

        // ============================================
        // AUTH - Google Sign In
        // ============================================
        function signInWithGoogle() {
            const provider = new firebase.auth.GoogleAuthProvider();
            auth.signInWithPopup(provider)
                .then(result => {
                    // handled by onAuthStateChanged
                })
                .catch(err => {
                    document.getElementById('login-error').innerHTML =
                        '<p style="color:#e94560">❌ ' + err.message + '</p>';
                });
        }

        function logout() {
            auth.signOut();
        }

        auth.onAuthStateChanged(async user => {
            if (user) {
                currentUser = user;
                document.getElementById('login-screen').style.display = 'none';
                document.getElementById('app').style.display = 'block';
                document.getElementById('user-name').textContent = '👤 ' + user.displayName;

                // Save user to backend
                await fetch(API + '/save-user', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        uid: user.uid,
                        name: user.displayName,
                        email: user.email
                    })
                });

                // Check payment status
                checkAccess();
            } else {
                currentUser = null;
                document.getElementById('login-screen').style.display = 'block';
                document.getElementById('app').style.display = 'none';
            }
        });

        async function checkAccess() {
            if (!currentUser) return;
            const res = await fetch(API + '/check-access', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: currentUser.uid})
            });
            const data = await res.json();
            const div = document.getElementById('access-status');
            if (data.paid) {
                div.innerHTML = '<p class="green">✅ Active subscription</p>';
            } else {
                div.innerHTML = '<p class="yellow">⚠️ No active subscription</p>';
            }
        }

        // ============================================
        // PAYMENT
        // ============================================
        async function startPayment() {
            if (!currentUser) return;
            const div = document.getElementById('presult');
            div.innerHTML = '<p>Creating order...</p>';
            const res = await fetch(API + '/create-order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({amount: 9900, user_id: currentUser.uid})
            });
            const order = await res.json();
            if (!order.id) { div.innerHTML = '<p class="red">❌ Failed: ' + (order.error || '') + '</p>'; return; }
            new Razorpay({
                key: order.key,
                amount: order.amount,
                currency: "INR",
                order_id: order.id,
                name: "BhashaBridge",
                description: "Monthly Subscription",
                handler: async function(response) {
                    const verify = await fetch(API + '/verify-payment', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            order_id: order.id,
                            payment_id: response.razorpay_payment_id,
                            user_id: currentUser.uid
                        })
                    });
                    const result = await verify.json();
                    if (result.success) {
                        div.innerHTML = '<p class="green">✅ Payment successful!</p>';
                        checkAccess();
                    } else {
                        div.innerHTML = '<p class="red">❌ Verification failed</p>';
                    }
                },
                prefill: { name: currentUser.displayName, email: currentUser.email },
                theme: { color: "#e94560" }
            }).open();
        }

        // ============================================
        // VOICE CLONE
        // ============================================
        async function cloneVoice() {
            if (!currentUser) return;
            const file = document.getElementById('audiofile').files[0];
            const div = document.getElementById('vresult');
            if (!file) { div.innerHTML = '<p class="red">Please select audio file</p>'; return; }
            div.innerHTML = '<p>Cloning... please wait</p>';
            const form = new FormData();
            form.append('audio', file);
            form.append('user_id', currentUser.uid);
            form.append('name', currentUser.displayName);
            const res = await fetch(API + '/clone', {method: 'POST', body: form});
            const data = await res.json();
            if (data.success) div.innerHTML = '<p class="green">✅ Voice cloned successfully!</p>';
            else div.innerHTML = '<p class="red">❌ ' + (data.error || 'Failed') + '</p>';
        }

        // ============================================
        // TRANSLATE
        // ============================================
        async function translate() {
            if (!currentUser) return;
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
                body: JSON.stringify({text, from_lang: from, to_lang: to, target_user: target})
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

        // ============================================
        // CALL
        // ============================================
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
# SARVAM AI - Translation
# ============================================
def translate_with_sarvam(text, from_lang, to_lang):
    try:
        response = requests.post(
            "https://api.sarvam.ai/translate",
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
# ELEVENLABS - Voice cloning + TTS
# ============================================
def clone_with_elevenlabs(audio_bytes, name):
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
            return response.content
        return None
    except Exception as e:
        print(f"Speech error: {e}")
        return None

# ============================================
# EXOTEL - Phone calls
# ============================================
def call_with_exotel(from_phone, to_phone):
    try:
        if not from_phone.startswith("+"):
            from_phone = "+91" + from_phone.lstrip("0")
        if not to_phone.startswith("+"):
            to_phone = "+91" + to_phone.lstrip("0")
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
# ROUTES
# ============================================

@app.route("/")
def homepage():
    return render_template_string(
        WEB_PAGE,
        firebase_api_key=FIREBASE_API_KEY,
        firebase_auth_domain=FIREBASE_AUTH_DOMAIN,
        firebase_project_id=FIREBASE_PROJECT_ID,
        firebase_app_id=FIREBASE_APP_ID
    )

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "BhashaBridge"})

@app.route("/save-user", methods=["POST"])
def save_user_route():
    data = request.json
    save_user(data.get("uid"), data.get("name"), data.get("email"))
    return jsonify({"success": True})

@app.route("/clone", methods=["POST"])
def clone_voice():
    audio_file = request.files.get("audio")
    user_id = request.form.get("user_id", "")
    name = request.form.get("name", user_id)
    if not audio_file:
        return jsonify({"success": False, "error": "No audio file uploaded"})
    audio_bytes = audio_file.read()
    voice_id = clone_with_elevenlabs(audio_bytes, name)
    if voice_id:
        save_voice(user_id, voice_id)
        return jsonify({"success": True, "voice_id": voice_id})
    return jsonify({"success": False, "error": "Voice cloning failed"})

@app.route("/translate", methods=["POST"])
def translate():
    data = request.json
    text = data.get("text", "")
    from_lang = data.get("from_lang", "en-IN")
    to_lang = data.get("to_lang", "hi-IN")
    target_user = data.get("target_user", "")
    if not text:
        return jsonify({"success": False, "error": "No text provided"})
    translated = translate_with_sarvam(text, from_lang, to_lang)
    audio_base64 = None
    if target_user:
        voice_id = get_voice_by_name(target_user)
        if voice_id:
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
    data = request.json
    from_phone = data.get("from", "")
    to_phone = data.get("to", "")
    if not from_phone or not to_phone:
        return jsonify({"success": False, "error": "Both phone numbers required"})
    success = call_with_exotel(from_phone, to_phone)
    log_call(from_phone, to_phone, "success" if success else "failed")
    if success:
        return jsonify({"success": True, "message": "Call initiated"})
    return jsonify({"success": False, "error": "Failed to make call"})

@app.route("/create-order", methods=["POST"])
def create_order():
    try:
        import razorpay
        data = request.json
        amount = data.get("amount", 9900)
        user_id = data.get("user_id", "")
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })
        order["key"] = RAZORPAY_KEY_ID
        save_payment(user_id, order["id"], amount, "pending")
        return jsonify(order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    try:
        import razorpay
        data = request.json
        order_id = data.get("order_id")
        payment_id = data.get("payment_id")
        user_id = data.get("user_id")
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        payment = client.payment.fetch(payment_id)
        if payment["status"] == "captured":
            update_payment_status(order_id, "paid")
            return jsonify({"success": True})
        return jsonify({"success": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/check-access", methods=["POST"])
def check_access():
    data = request.json
    user_id = data.get("user_id", "")
    paid = is_user_paid(user_id)
    return jsonify({"paid": paid})

# ============================================
# START SERVER
# ============================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    @app.route("/check-voice", methods=["POST"])
def check_voice():
    data = request.json
    user_id = data.get("user_id", "")
    voice_id = get_voice_by_uid(user_id)
    return jsonify({"has_voice": voice_id is not None})
