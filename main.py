# app.py - Clean Flask backend that uses environment variable API key
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
from uuid import uuid4
import base64
from dotenv import load_dotenv
import sys

# Load environment variables from .env file
# Try different paths to find .env file
env_paths = [
    '.env',  # Current directory
    '/home/' + os.path.expanduser('~').split('/')[-1] + '/interviewpractivepython/.env',  # Absolute path
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')  # Same directory as app.py
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        env_loaded = True
        print(f"✅ Loaded .env from: {env_path}")
        break

if not env_loaded:
    print("⚠️ No .env file found, using system environment variables")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
PORT = int(os.environ.get('PORT', 3000))
CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Debug: Check if API keys are loaded
print(f"🔑 Claude API Key loaded: {'✅ Yes' if CLAUDE_API_KEY else '❌ No'}")
if CLAUDE_API_KEY:
    print(f"🔑 Claude key starts with: {CLAUDE_API_KEY[:15]}...")
else:
    print("💡 Set environment variable: CLAUDE_API_KEY=sk-ant-api03-your-key")

print(f"🔑 OpenAI API Key loaded: {'✅ Yes' if OPENAI_API_KEY else '❌ No'}")
if OPENAI_API_KEY:
    print(f"🔑 OpenAI key starts with: {OPENAI_API_KEY[:15]}...")
else:
    print("💡 Set environment variable: OPENAI_API_KEY=sk-proj-your-key")

# Remove all audio file/directory management. Only in-memory audio is used.
def text_to_speech_openai(text, voice="nova", model="gpt-4o-mini-tts"):
    """Convert text to speech using OpenAI TTS and return base64-encoded MP3 audio."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured in environment!")
    response = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        json={
            "model": model,
            "input": text,
            "voice": voice,
            "instructions":
                "Use clear and slow delivery such that a non native speaker can follow along. Also make sure the tone is very positive and encouraging to help the student",
            "response_format": "mp3"
        },
        timeout=60
    )
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI TTS error: {response.status_code} {response.text}")
    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return audio_base64

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory('.', 'interviewPy.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory('.', filename)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/check_answer', methods=['POST'])
def check_answer():
    """Check student's grammar answer using Claude AI"""
    try:
        print("Received request to Claude API")
        if not CLAUDE_API_KEY:
            print("❌ Claude API key not configured in environment!")
            return jsonify({
                'error': 'Service not configured',
                'details': 'Claude API key not found. Please contact administrator.'
            }), 503
        if not OPENAI_API_KEY:
            print("❌ OpenAI API key not configured in environment!")
            return jsonify({
                'error': 'Service not configured',
                'details': 'OpenAI API key not found. Please contact administrator.'
            }), 503
        print(f"✅ Using API key from environment: {CLAUDE_API_KEY[:15]}...")
        data = request.get_json()
        print(f"📥 Received data keys: {list(data.keys()) if data else 'None'}")
        if not data:
            print("❌ No JSON data in request")
            return jsonify({'error': 'No JSON data provided'}), 400
        # Extract question and user_answer
        question = data.get('question')
        user_answer = data.get('user_answer')
        if not question or not user_answer:
            print("❌ Missing question or user_answer in request")
            return jsonify({'error': 'Both question and user_answer are required'}), 400
        # Construct prompt
        prompt = f"""I'm helping a student practice grammar. Here's the question and their answer:\n\nQuestion: "{question}"
Student's answer: "{user_answer}"
\nPlease provide concise, encouraging feedback.\n- If the student's answer is correct, reply with a short confirmation only (no explanation needed).\n- If the answer is incorrect, briefly explain what was wrong and provide the correct answer.\n- Always keep your response as short and helpful as possible for a grammar learner."""
        print(f"📝 Constructed prompt:\n{prompt}")
        # Prepare Claude API call
        model = 'claude-sonnet-4-20250514'
        max_tokens = 300
        claude_url = 'https://api.anthropic.com/v1/messages'
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': CLAUDE_API_KEY,  # 🔑 FROM ENVIRONMENT VARIABLE ONLY
            'anthropic-version': '2023-06-01'
        }
        payload = {
            'model': model,
            'max_tokens': max_tokens,
            'messages': [{
                'role': 'user',
                'content': prompt
            }]
        }
        print(f"🚀 Making request to Claude API...")
        
        # Make request to Claude API
        response = requests.post(claude_url, headers=headers, json=payload, timeout=30)
        
        print(f"📡 Claude API response status: {response.status_code}")
        
        if response.status_code != 200:
            error_text = response.text
            print(f"❌ Claude API error: {response.status_code}")
            print(f"❌ Error details: {error_text}")
            return jsonify({
                'error': f'Claude API error: {response.status_code}',
                'details': error_text
            }), response.status_code
        
        # Return Claude's response
        claude_response = response.json()
        print("✅ Successfully got response from Claude API")
        # Extract feedback text
        feedback = None
        if 'content' in claude_response and isinstance(claude_response['content'], list) and len(claude_response['content']) > 0:
            feedback = claude_response['content'][0].get('text')
        if not feedback:
            print("❌ No feedback text in Claude response")
            return jsonify({'error': 'No feedback text from Claude'}), 500
        # Convert feedback to speech using OpenAI TTS (in memory)
        try:
            audio_base64 = text_to_speech_openai(feedback)
        except Exception as tts_err:
            print(f"❌ OpenAI TTS error: {tts_err}")
            audio_base64 = None
        return jsonify({
            'text': feedback,
            'audio_base64': audio_base64
        })
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {str(e)}")
        return jsonify({
            'error': 'Request failed',
            'details': str(e)
        }), 500
    
    except Exception as e:
        print(f"❌ Server error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/test-api-key')
def test_api_key():
    """Test endpoint to verify API key is loaded"""
    return jsonify({
        'api_key_set': bool(CLAUDE_API_KEY),
        'api_key_length': len(CLAUDE_API_KEY) if CLAUDE_API_KEY else 0,
        'api_key_starts_with': CLAUDE_API_KEY[:15] + '...' if CLAUDE_API_KEY else 'None'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'message': 'Grammar app Python backend is running',
        'api_configured': bool(CLAUDE_API_KEY)
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/tts', methods=['POST'])
def tts_openai():
    """
    Simple endpoint to test OpenAI TTS: POST { "text": "your text" }
    Returns: { "audio_base64": ... }
    """
    try:
        data = request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        audio_base64 = text_to_speech_openai(text)
        return jsonify({'audio_base64': audio_base64})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio():
    """
    Generate audio file from text using OpenAI TTS
    POST { "text": "your text" }
    Returns: MP3 audio file directly
    """
    try:
        data = request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate audio using same function as check_answer
        if not OPENAI_API_KEY:
            return jsonify({'error': 'OpenAI API key not configured'}), 503
            
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            json={
                "model": "gpt-4o-mini-tts",
                "input": text,
                "voice": "nova",
                "instructions":
                    "Use clear and slow delivery such that a non native speaker can follow along. Also make sure the tone is very positive and encouraging to help the student",
                "response_format": "mp3"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return jsonify({'error': f'OpenAI TTS error: {response.status_code}'}), 500
        
        # Return raw MP3 audio
        return response.content, 200, {'Content-Type': 'audio/mpeg'}
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Grammar app Python backend starting...")
    print(f"📝 Open http://localhost:{PORT}/grammar-practice.html to use the app")
    print(f"🏥 Health check available at http://localhost:{PORT}/health")
    print(f"🔧 API key test available at http://localhost:{PORT}/test-api-key")
    
    # Final check of API key
    if CLAUDE_API_KEY:
        print(f"✅ Claude API key configured (starts with: {CLAUDE_API_KEY[:15]}...)")
    else:
        print("❌ Claude API key NOT configured!")
        print("💡 Set environment variable: export CLAUDE_API_KEY=sk-ant-api03-your-key")
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=True,
        threaded=True
    )