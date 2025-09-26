# app.py - Clean Flask backend that uses environment variable API key
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import base64
from dotenv import load_dotenv

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
    print("routing in / ")
    """Serve the accessible landing page"""
    return send_from_directory('.', 'home.html')

@app.route('/tense')
def tense_page():
    """Serve tense practice page"""
    return send_from_directory('.', 'grammar-simple.html')

@app.route('/preposition')
def preposition_page():
    """Serve preposition practice page (simple placeholder)"""
    return send_from_directory('.', 'preposition.html')

@app.route('/grammar-simple.html')
def grammar_simple_redirect():
    """Serve home.html for the old grammar-simple.html link"""
    return send_from_directory('.', 'home.html')

@app.route('/api/weather',methods=['GET','POST'])
def show_weather_report():
    if request.method == 'POST':
        data = request.get_json()
        zip_code = data.get('zip')
    else:
        zip_code = request.args.get('zip')
    
    print(f"getting weather report for {zip_code}")
    return jsonify({
        'zip': zip_code,
        'weather': 'Nice and Sunny'
    })


@app.route('/<path:filename>')
def serve_static(filename):
    print(f"routing in serve_static :{filename}")
    """Serve static files"""
    try:
        return send_from_directory('./static', filename)
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
        # Construct prompt - using string formatting to avoid f-string issues with curly braces
        prompt = """I'm helping a student practice grammar. Here's the question and their answer:

Question: "{}"
Student's answer: "{}"

Please provide:
1. Concise, encouraging feedback on their answer
2. Generate the next grammar question for continued practice

For feedback:
- If correct: short confirmation only (no explanation needed)
- If incorrect: briefly explain what was wrong and provide the correct answer
- Keep feedback encouraging and concise

For the next question:
- IMPORTANT: Test a DIFFERENT English tense from what was just asked. Cycle through these systematically in order:
  1. Present simple (I work)
  2. Present continuous (I am working) 
  3. Present perfect (I have worked)
  4. Present perfect continuous (I have been working)
  5. Past simple (I worked)
  6. Past continuous (I was working)
  7. Past perfect (I had worked)
  8. Past perfect continuous (I had been working)
  9. Future simple (I will work)
  10. Future continuous (I will be working)
  11. Future perfect (I will have worked)
  12. Future perfect continuous (I will have been working)
- Use a different common verb (work, live, study, travel, cook, read, write, play, watch, etc.)
- Keep the question concise and clear
- Format: "Use '[verb]' in the [exact tense name] to describe [specific context]"
- Make the context relatable and practical
- Ensure you're testing a completely different tense structure than the previous question

Return your response as valid JSON in this exact format:
{{
  "feedback": "your encouraging feedback here",
  "next_question": "the new grammar question"
}}""".format(question, user_answer)
        print(f"📝 Constructed prompt:\n{prompt}")
        # Prepare Claude API call
        model = 'claude-sonnet-4-20250514'
        max_tokens = 500
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
        # Extract response text
        response_text = None
        if 'content' in claude_response and isinstance(claude_response['content'], list) and len(claude_response['content']) > 0:
            response_text = claude_response['content'][0].get('text')
        if not response_text:
            print("❌ No response text in Claude response")
            return jsonify({'error': 'No response text from Claude'}), 500
        
        print(f"📋 Claude response:\n{response_text}")
        
        # Parse JSON response from Claude
        try:
            import json
            claude_data = json.loads(response_text)
            feedback = claude_data.get('feedback', '')
            next_question = claude_data.get('next_question', '')
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON from Claude: {e}")
            # Fallback: use entire response as feedback
            feedback = response_text
            next_question = ""
        
        print(f"✅ Parsed feedback: {feedback}")
        print(f"✅ Parsed next question: {next_question}")
        
        # Create combined text for TTS: feedback, pause, then next question
        combined_text = feedback
        if next_question:
            combined_text += f". Next question: {next_question}"
        
        # Convert combined text to speech using OpenAI TTS (in memory)
        try:
            audio_base64 = text_to_speech_openai(combined_text)
        except Exception as tts_err:
            print(f"❌ OpenAI TTS error: {tts_err}")
            audio_base64 = None
        
        return jsonify({
            'text': feedback,
            'next_question': next_question,
            'combined_text': combined_text,
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

@app.route('/api/check_preposition', methods=['POST'])
def check_preposition():
    """Check student's preposition answer and generate the next one."""
    try:
        if not CLAUDE_API_KEY or not OPENAI_API_KEY:
            return jsonify({'error': 'Service not configured'}), 503

        data = request.get_json() or {}
        question = data.get('question')
        user_answer = data.get('user_answer')
        next_preposition = (data.get('next_preposition') or '').strip()
        if not question or not user_answer:
            return jsonify({'error': 'Both question and user_answer are required'}), 400

        prompt = (
            "You are a gentle English tutor for a visually impaired student.\n"
            "Task: Evaluate the student's use of prepositions and give the next question.\n\n"
            f"Question: \"{question}\"\n"
            f"Student's answer: \"{user_answer}\"\n\n"
            "Return JSON with keys: feedback and next_question.\n"
            "IMPORTANT: next_question must follow this exact format: \n"
            "\"\"<preposition>\" is used for <short rule>. Example: \"<example 1>\" or \"<example 2>\". Can you make your own sentence with \"<preposition>\"?\"\n"
            "You MUST generate the next question USING EXACTLY this preposition (do not choose a different one):\n"
            f"next_preposition: {next_preposition if next_preposition else '[choose a different one than current]'}\n"
            "Keep sentences simple and practical."
        )

        model = 'claude-sonnet-4-20250514'
        claude_url = 'https://api.anthropic.com/v1/messages'
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': CLAUDE_API_KEY,
            'anthropic-version': '2023-06-01'
        }
        payload = {
            'model': model,
            'max_tokens': 400,
            'messages': [{'role': 'user', 'content': prompt}]
        }

        response = requests.post(claude_url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return jsonify({'error': 'Claude API error', 'details': response.text}), response.status_code

        resp_json = response.json()
        text = None
        if 'content' in resp_json and isinstance(resp_json['content'], list) and resp_json['content']:
            text = resp_json['content'][0].get('text')
        if not text:
            return jsonify({'error': 'No response text from Claude'}), 500

        import json as _json, re as _re
        feedback = ''
        next_question = ''
        # Try to strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith('```'):
            # remove the first and last code fences
            cleaned = _re.sub(r'^```[a-zA-Z0-9_\-]*\n', '', cleaned)
            cleaned = _re.sub(r'\n```\s*$', '', cleaned)
        # Try direct JSON parse
        try:
            parsed = _json.loads(cleaned)
            feedback = str(parsed.get('feedback', ''))
            next_question = str(parsed.get('next_question', ''))
        except Exception:
            # Try to extract JSON object substring
            m = _re.search(r'\{[\s\S]*\}', cleaned)
            if m:
                try:
                    parsed = _json.loads(m.group(0))
                    feedback = str(parsed.get('feedback', ''))
                    next_question = str(parsed.get('next_question', ''))
                except Exception:
                    feedback = cleaned
            else:
                # Fallback: try to parse simple key lines
                fb = _re.search(r'feedback\s*[:=-]\s*"?([^\n"]+)"?', cleaned, _re.IGNORECASE)
                nq = _re.search(r'next_?question\s*[:=-]\s*"?([^\n"]+)"?', cleaned, _re.IGNORECASE)
                if fb: feedback = fb.group(1)
                if nq: next_question = nq.group(1)
                if not feedback and not next_question:
                    feedback = cleaned

        # Sanitize to avoid stray brackets/quotes in TTS
        def _sanitize(s: str) -> str:
            s = s.strip()
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1]
            return s
        feedback = _sanitize(feedback)
        next_question = _sanitize(next_question)
        combined_text = feedback + (f". Next question: {next_question}" if next_question else '')
        try:
            audio_base64 = text_to_speech_openai(combined_text)
        except Exception:
            audio_base64 = None

        return jsonify({
            'text': feedback,
            'next_question': next_question,
            'combined_text': combined_text,
            'audio_base64': audio_base64
        })
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

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

if __name__ == '__main__':
    print("🚀 Grammar app Python backend starting...")
    print(f"📝 Open http://localhost:{PORT}/ to use the app")
    print(f"🏥 Health check available at http://localhost:{PORT}/health")
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=True,
        threaded=True
    )