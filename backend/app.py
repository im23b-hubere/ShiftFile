import os
from flask import Flask, request, send_file, jsonify, send_from_directory
from PIL import Image
import uuid
import logging
import sys
import mimetypes
from pydub import AudioSegment
import tempfile
from werkzeug.utils import secure_filename
import traceback
from dotenv import load_dotenv
import cloudconvert

# Load environment variables
load_dotenv()

# Set FFmpeg path for local development
if os.getenv('ENVIRONMENT') == 'development':
    AudioSegment.converter = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"

# Configure CloudConvert
if os.getenv('CLOUDCONVERT_API_KEY'):
    cloudconvert.configure(api_key=os.getenv('CLOUDCONVERT_API_KEY'))

# Verzeichnisse konfigurieren
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
CONVERTED_DIR = os.path.join(BASE_DIR, 'converted')

# Verzeichnisse erstellen
for directory in [TEMP_DIR, UPLOAD_DIR, CONVERTED_DIR]:
    os.makedirs(directory, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Logging-Konfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Erweiterte Dateiformat-Unterstützung
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'tiff', 'bmp', 'ico'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_AUDIO_EXTENSIONS)

# Format-Mapping für Pillow
FORMAT_MAPPING = {
    'jpg': 'JPEG',
    'jpeg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'gif': 'GIF',
    'bmp': 'BMP',
    'ico': 'ICO'
}

@app.route('/')
def index():
    """Serve the frontend"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    try:
        return send_from_directory(FRONTEND_DIR, path)
    except:
        return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/formats')
def get_formats():
    """Get supported formats"""
    return jsonify({
        'image': list(ALLOWED_IMAGE_EXTENSIONS),
        'audio': list(ALLOWED_AUDIO_EXTENSIONS)
    })

@app.route('/convert', methods=['POST'])
def convert_file():
    """Handle file conversion"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei gefunden'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Nicht unterstütztes Dateiformat'}), 400

        # Log request details
        logging.info(f"Konvertierungsanfrage: {file.filename}")
        logging.info(f"Parameter: {request.form}")

        # Create temp files with correct extensions
        input_ext = os.path.splitext(file.filename)[1].lower()
        temp_input = os.path.join(TEMP_DIR, f"input_{uuid.uuid4()}{input_ext}")
        file.save(temp_input)
        
        target_format = request.form.get('format', 'png').lower()
        temp_output = os.path.join(TEMP_DIR, f"output_{uuid.uuid4()}.{target_format}")

        try:
            if is_image_file(file.filename):
                logging.info(f"Konvertiere Bild von {input_ext} nach {target_format}")
                
                # Öffne das Bild und konvertiere es
                with Image.open(temp_input) as img:
                    # Konvertiere RGBA zu RGB für JPG
                    if target_format in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA']:
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[3])
                        else:
                            background.paste(img, mask=img.split()[1])
                        img = background
                    
                    # Speichere das konvertierte Bild
                    pillow_format = FORMAT_MAPPING.get(target_format, target_format.upper())
                    img.save(temp_output, format=pillow_format)
                    logging.info(f"Bild erfolgreich konvertiert: {temp_output}")
            
            elif is_audio_file(file.filename):
                if os.getenv('ENVIRONMENT') == 'development':
                    # Local audio processing
                    audio = AudioSegment.from_file(temp_input)
                    
                    # Process audio parameters
                    volume_db = float(request.form.get('volume', 0))
                    speed = float(request.form.get('speed', 1.0))
                    fade_in = int(request.form.get('fadeIn', 0))
                    fade_out = int(request.form.get('fadeOut', 0))
                    normalize = request.form.get('normalize', 'false').lower() == 'true'
                    mono = request.form.get('mono', 'false').lower() == 'true'
                    
                    if volume_db != 0:
                        audio = audio.apply_gain(volume_db)
                    
                    if speed != 1.0:
                        audio = audio._spawn(audio.raw_data, overrides={
                            "frame_rate": int(audio.frame_rate * speed)
                        })
                    
                    if fade_in > 0:
                        audio = audio.fade_in(fade_in * 1000)
                    
                    if fade_out > 0:
                        audio = audio.fade_out(fade_out * 1000)
                    
                    if normalize:
                        audio = audio.normalize()
                    
                    if mono:
                        audio = audio.set_channels(1)
                    
                    # Export with format-specific settings
                    export_params = {}
                    if target_format == 'mp3':
                        bitrate = request.form.get('bitrate', '192k')
                        export_params['bitrate'] = bitrate
                    
                    audio.export(temp_output, format=target_format, **export_params)
                else:
                    # Cloud audio processing
                    try:
                        job = cloudconvert.Job.create({
                            'tasks': {
                                'import-file': {
                                    'operation': 'import/upload'
                                },
                                'convert-file': {
                                    'operation': 'convert',
                                    'input': ['import-file'],
                                    'output_format': target_format,
                                    'audio_codec': target_format,
                                    'audio_bitrate': request.form.get('bitrate', '192'),
                                    'audio_normalize': request.form.get('normalize', 'false').lower() == 'true',
                                    'audio_channels': 1 if request.form.get('mono', 'false').lower() == 'true' else 2
                                },
                                'export-file': {
                                    'operation': 'export/url',
                                    'input': ['convert-file']
                                }
                            }
                        })

                        upload_task = job['tasks']['import-file']
                        with open(temp_input, 'rb') as file:
                            cloudconvert.Task.upload(file=file, task=upload_task)
                        
                        job = cloudconvert.Job.wait(id=job['id'])
                        export_task = job['tasks']['export-file']
                        
                        # Download the converted file
                        cloudconvert.download(filename=temp_output, url=export_task['result']['files'][0]['url'])
                        
                    except Exception as e:
                        logging.error(f"Cloud conversion error: {str(e)}")
                        raise

            # Send the converted file
            return send_file(
                temp_output,
                as_attachment=True,
                download_name=f"converted_{secure_filename(file.filename)}"
            )

        except Exception as e:
            logging.error(f"Konvertierungsfehler: {str(e)}")
            logging.error(traceback.format_exc())
            return jsonify({'error': f'Fehler bei der Konvertierung: {str(e)}'}), 500

        finally:
            # Cleanup temp files
            try:
                if os.path.exists(temp_input):
                    os.remove(temp_input)
                if os.path.exists(temp_output):
                    os.remove(temp_output)
            except Exception as e:
                logging.error(f"Fehler beim Aufräumen: {str(e)}")

    except Exception as e:
        logging.error(f"Allgemeiner Fehler: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS

def is_image_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_IMAGE_EXTENSIONS

def is_audio_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_AUDIO_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000) 