from flask import Flask, render_template, request, jsonify, send_file
import requests
import os
import io

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

LAST_VALID_KEY = ""
VOICE_SLOTS = {}
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/check_key', methods=['POST'])
def check_key():
    global LAST_VALID_KEY
    data = request.get_json(silent=True) or request.form
    api_key = (data.get('api_key') or data.get('apiKey') or data.get('key') or '').strip()
    
    if not api_key:
        return jsonify({'valid': False, 'error': 'Key လိုအပ်ပါသည်'})

    headers = {'xi-api-key': api_key}
    try:
        res = requests.get('https://api.elevenlabs.io/v1/user/subscription', headers=headers, timeout=10)
        if res.status_code == 200:
            user_data = res.json()
            remaining = user_data.get('character_limit', 0) - user_data.get('character_count', 0)
            LAST_VALID_KEY = api_key
            return jsonify({'valid': True, 'remaining': remaining})
        else:
            return jsonify({'valid': False, 'error': 'Invalid API Key'})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})

@app.route('/api/upload_slot', methods=['POST'])
def upload_slot():
    global LAST_VALID_KEY, VOICE_SLOTS
    try:
        api_key = (request.form.get('api_key') or request.form.get('apiKey') or request.form.get('key') or LAST_VALID_KEY).strip()
        slot = request.form.get('slot', 'clone1')
        file = request.files.get('voice_file') or request.files.get('file')

        if not file:
            return jsonify({'success': False, 'error': 'အသံဖိုင် ရွေးချယ်ထားခြင်း မရှိပါ'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, f"{slot}.mp3")
        file.save(filepath)

        if api_key:
            headers = {'xi-api-key': api_key}
            with open(filepath, 'rb') as f:
                files = {'files': (file.filename, f, file.content_type)}
                data = {'name': f"Voice_{slot}"}
                response = requests.post('https://api.elevenlabs.io/v1/voices/add', headers=headers, data=data, files=files)
                
                if response.status_code == 200:
                    v_id = response.json().get('voice_id')
                    VOICE_SLOTS[slot] = v_id
                    return jsonify({'success': True, 'voice_id': v_id, 'slot': slot})

        return jsonify({'success': True, 'slot': slot, 'filename': f"{slot}.mp3"})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_audio():
    global LAST_VALID_KEY, VOICE_SLOTS
    try:
        data = request.get_json(silent=True) or request.form
        api_key = (data.get('api_key') or data.get('apiKey') or data.get('key') or LAST_VALID_KEY).strip()
        text = (data.get('text') or data.get('prompt') or '').strip()
        raw_voice = (data.get('voice_id') or data.get('voice') or '').strip()

        if raw_voice in VOICE_SLOTS:
            voice_id = VOICE_SLOTS[raw_voice]
        elif raw_voice and not raw_voice.startswith('clone'):
            voice_id = raw_voice
        else:
            voice_id = DEFAULT_VOICE_ID

        if not api_key:
            return jsonify({'error': 'API Key ထည့်သွင်းပေးပါ'}), 400
        if not text:
            return jsonify({'error': 'အသံပြောင်းလိုသော စာသားကို ရိုက်ထည့်ပေးပါ'}), 400

        headers = {
            'xi-api-key': api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2"
        }

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return send_file(
                io.BytesIO(response.content),
                mimetype='audio/mpeg',
                as_attachment=False
            )
        else:
            return jsonify({'error': response.text}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
