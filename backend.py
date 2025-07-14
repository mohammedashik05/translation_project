from flask import Flask, request, jsonify, send_file
import os
import time
from deep_translator import GoogleTranslator
from gtts import gTTS
import assemblyai as aai
import tempfile
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set AssemblyAI API Key
aai.settings.api_key = "e518225f93a7463d874f7edd1f9608b7"  
RENDER_URL = os.getenv("RENDER_URL", "https://kiranraj-eng-totam-1.onrender.com")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Ensure 'uploads' and 'audio' folders exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')
if not os.path.exists('audio'):
    os.makedirs('audio')

@app.route('/process-video', methods=['POST'])
def process_video():
    """ Handles video upload, transcription, translation, and text-to-speech generation """
    
    # Check if a video file is uploaded
    if 'video' not in request.files:
        return jsonify({'error': 'No video file part'}), 400

    video_file = request.files['video']
    
    # Validate file selection
    if video_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    video_path = os.path.join('uploads', video_file.filename)
    
    # Save the uploaded video
    video_file.save(video_path)

    try:
        # Step 1: Transcribe video to English text using AssemblyAI
        transcript = transcribe_video(video_path)
        if 'error' in transcript:
            return jsonify({'error': transcript['error']}), 500
        
        english_text = transcript['text']

        # Step 2: Translate transcript to Tamil using Google Translator
        translated_text = GoogleTranslator(source='auto', target='ta').translate(english_text)

        # Step 3: Convert Tamil text to audio using gTTS
        audio_path = generate_audio(translated_text)

        return jsonify({
            'english_text': english_text,
            'tamil_text': translated_text,
           'audio_url': f"{RENDER_URL}/audio/{os.path.basename(audio_path)}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Ensure the file is properly deleted after processing
        time.sleep(5)  # Wait to prevent "file in use" errors
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception as e:
                print(f"Error deleting file: {e}")

# Function to transcribe video using AssemblyAI
def transcribe_video(video_path):
    """ Transcribes video using AssemblyAI and returns the text """
    
    transcriber = aai.Transcriber()
    
    # Open file safely and transcribe
    with open(video_path, 'rb') as video_file:
        transcript = transcriber.transcribe(video_file)

    if transcript.status == aai.TranscriptStatus.error:
        return {'error': transcript.error}
    
    return {'text': transcript.text}

# Function to convert Tamil text to audio using gTTS
def generate_audio(text):
    tts = gTTS(text=text, lang='ta')

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
        audio_path = temp_file.name
        tts.save(audio_path)

    return audio_path 

@app.route('/audio/<filename>', methods=['GET'])
def get_audio(filename):
    """ Serves the generated Tamil audio file """
    audio_path = os.path.join('audio', filename)
    if os.path.exists(audio_path):
        return send_file(audio_path, as_attachment=True)
    else:
        return jsonify({'error': 'Audio file not found'}), 404

if __name__ == '__main__':
     port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
     app.run(host="0.0.0.0", port=port, debug=True)

