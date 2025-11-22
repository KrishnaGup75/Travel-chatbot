from flask import Flask, render_template, request, send_from_directory, jsonify
import google.generativeai as genai
from gtts import gTTS
import os
import uuid
import re

app = Flask(__name__)

api_key = "AIzaSyB6iB1SsCkEWOBsPfcrPgVwHOkqpSpg1Cs"
genai.configure(api_key=api_key)

try:
    client = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"Error initializing GenerativeModel: {e}")
    client = None

DATA_FILE = "data.txt"
VOICE_DIR = "static/voices"
os.makedirs(VOICE_DIR, exist_ok=True)


def clean_text_for_audio(text):
    """Remove emojis, symbols, and special characters but keep words, numbers, and basic punctuation."""
    # Keep only letters, numbers, spaces, and common punctuation (. , ! ? ' -)
    cleaned = re.sub(r'[^\w\s\.\,\!\?\'\-]', '', text, flags=re.UNICODE)
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def format_bot_response(text):
    """Convert markdown-style formatting to HTML tags for display."""
    # Convert **text** to <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Convert *text* to <em>text</em> (but not if it's part of **)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    return text


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
        open(DATA_FILE, "w", encoding="utf-8").close()

    with open(DATA_FILE, "r", encoding="utf-8") as fi:
        raw_conversation = fi.read()

    conversation_list = parse_conversation(raw_conversation)
    return render_template('index1.html', conversation=conversation_list)

@app.route('/chat', methods=['POST'])
def chat():
    prompt = request.form.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Empty prompt"}), 400

    with open(DATA_FILE, "r", encoding="utf-8") as fi:
        chat_history = fi.read()

    pre_prompt = f"""
You are a digital Tourism Expert.
Be concise and friendly.

Conversation history:
{chat_history}

User: {prompt}
"""

    try:
        response = client.generate_content(pre_prompt)
        bot_response = response.text
    except Exception as e:
        bot_response = f"Error generating response: {e}"

    # Format the response for display (convert markdown to HTML)
    formatted_response = format_bot_response(bot_response)

    #Voice Generation
    audio_filename = f"{uuid.uuid4()}.mp3"
    audio_path = os.path.join(VOICE_DIR, audio_filename)

    try:
        # Clean the text before converting to speech (remove emojis and symbols)
        clean_text = clean_text_for_audio(bot_response)
        tts = gTTS(text=clean_text, lang='en')
        tts.save(audio_path)
    except Exception as e:
        print("TTS Error:", e)
        audio_filename = None

    with open(DATA_FILE, "a", encoding="utf-8") as file:
        file.write(f"User: {prompt}\n")
        file.write(f"Bot: {bot_response}\n")

    return jsonify({
        "user": prompt,
        "bot": formatted_response,
        "audio": f"/voices/{audio_filename}" if audio_filename else None
    })


@app.route('/voices/<filename>')
def serve_audio(filename):
    return send_from_directory(VOICE_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True)
