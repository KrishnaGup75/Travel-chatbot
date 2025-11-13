from flask import Flask, render_template, request, send_from_directory, jsonify
import google.generativeai as genai
from gtts import gTTS
import os
import uuid

app = Flask(__name__)

# --- Configuration ---
api_key = "AIzaSyB6iB1SsCkEWOBsPfcrPgVwHOkqpSpg1Cs"
genai.configure(api_key=api_key)

# --- AI Model Initialization ---
try:
    client = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Error initializing GenerativeModel: {e}")
    client = None

DATA_FILE = "data.txt"
VOICE_DIR = "static/voices"
os.makedirs(VOICE_DIR, exist_ok=True)

def parse_conversation(file_content):
    messages = []
    current_message = None
    for line in file_content.splitlines():
        if line.startswith('User: '):
            if current_message:
                messages.append(current_message)
            current_message = {'speaker': 'User', 'text': line[6:]}
        elif line.startswith('Bot: '):
            if current_message:
                messages.append(current_message)
            current_message = {'speaker': 'Bot', 'text': line[5:]}
        elif current_message:
            current_message['text'] += '\n' + line
    if current_message:
        messages.append(current_message)
    return messages

@app.route('/', methods=['GET'])
def index():
    if not os.path.exists(DATA_FILE):
        open(DATA_FILE, "w").close()
    with open(DATA_FILE, "r") as fi:
        raw_conversation = fi.read()
    conversation_list = parse_conversation(raw_conversation)
    return render_template('index.html', conversation=conversation_list)

@app.route('/chat', methods=['POST'])
def chat():
    prompt = request.form['prompt']
    if not prompt.strip():
        return jsonify({"error": "Empty prompt"}), 400

    with open(DATA_FILE, "r") as fi:
        chat_history = fi.read()

    pre_prompt = f'''
You are a digital Tourism Expert. 
Be concise and friendly.

Conversation history:
{chat_history}

User: {prompt}
'''

    try:
        response = client.generate_content(pre_prompt)
        bot_response = response.text
    except Exception as e:
        bot_response = f"Error generating response: {e}"

    # --- Generate voice for bot ---
    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(VOICE_DIR, audio_filename)
    try:
        tts = gTTS(text=bot_response, lang='en')
        tts.save(audio_path)
    except Exception as e:
        print("TTS Error:", e)
        audio_filename = None

    # Save conversation
    with open(DATA_FILE, 'a') as file:
        file.write(f'User: {prompt}\n')
        file.write(f'Bot: {bot_response}\n')

    return jsonify({
        "user": prompt,
        "bot": bot_response,
        "audio": f"/voices/{audio_filename}" if audio_filename else None
    })

@app.route('/voices/<filename>')
def serve_audio(filename):
    return send_from_directory(VOICE_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)
