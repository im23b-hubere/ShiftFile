import os
from flask import Flask, request, send_file, jsonify, send_from_directory
from PIL import Image
import uuid
import logging
import sys
import mimetypes
import tempfile
from werkzeug.utils import secure_filename
import traceback
from dotenv import load_dotenv
import cloudconvert

# Load environment variables
load_dotenv()

# Configure CloudConvert
if not os.getenv('CLOUDCONVERT_API_KEY'):
    logging.error("CLOUDCONVERT_API_KEY nicht gefunden!")
else:
    cloudconvert.configure(api_key=os.getenv('CLOUDCONVERT_API_KEY'))

# Verzeichnisse konfigurieren
TEMP_DIR = '/tmp' if os.getenv('VERCEL_ENV') else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')

# Verzeichnis erstellen
os.makedirs(TEMP_DIR, exist_ok=True)

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
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logging.error(f"Error serving index.html: {str(e)}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    try:
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        logging.error(f"Error serving static file {path}: {str(e)}")
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/formats')
def get_formats():
    """Get supported formats"""
    return jsonify({
        'image': list(ALLOWED_IMAGE_EXTENSIONS),
        'audio': list(ALLOWED_AUDIO_EXTENSIONS)
    })

@app.route('/api/convert', methods=['POST'])
def convert_file():
    """Handle file conversion"""
    if not os.getenv('CLOUDCONVERT_API_KEY'):
        return jsonify({'error': 'CloudConvert API-Key nicht konfiguriert'}), 500

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
                logging.info(f"Konvertiere Audio von {input_ext} nach {target_format}")
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
                                'audio_channels': 1 if request.form.get('mono', 'false').lower() == 'true' else 2,
                                'volume': float(request.form.get('volume', 0)),
                                'trim_start': float(request.form.get('fadeIn', 0)),
                                'trim_end': float(request.form.get('fadeOut', 0))
                            },
                            'export-file': {
                                'operation': 'export/url',
                                'input': ['convert-file']
                            }
                        }
                    })

                    logging.info("Uploading file to CloudConvert...")
                    upload_task = job['tasks']['import-file']
                    with open(temp_input, 'rb') as file:
                        cloudconvert.Task.upload(file=file, task=upload_task)
                    
                    logging.info("Waiting for conversion...")
                    job = cloudconvert.Job.wait(id=job['id'])
                    export_task = job['tasks']['export-file']
                    
                    logging.info("Downloading converted file...")
                    cloudconvert.download(filename=temp_output, url=export_task['result']['files'][0]['url'])
                    logging.info("Audio conversion completed successfully")
                    
                except Exception as e:
                    logging.error(f"CloudConvert error: {str(e)}")
                    return jsonify({'error': f'Fehler bei der Cloud-Konvertierung: {str(e)}'}), 500

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