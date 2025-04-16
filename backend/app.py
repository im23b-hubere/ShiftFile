import os
from flask import Flask, request, send_file, jsonify
from PIL import Image
import uuid
import logging
import sys
import mimetypes
from pydub import AudioSegment
import tempfile
from werkzeug.utils import secure_filename

# Vercel-spezifische Konfiguration
TEMP_DIR = '/tmp' if os.getenv('VERCEL_ENV') else 'temp'
os.makedirs(TEMP_DIR, exist_ok=True)

app = Flask(__name__)
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

# Format-Mapping und Qualitätseinstellungen bleiben gleich
FORMAT_MAPPING = {
    'JPG': 'JPEG',
    'JPEG': 'JPEG',
    'PNG': 'PNG',
    'WEBP': 'WEBP',
    'GIF': 'GIF',
    'TIFF': 'TIFF',
    'BMP': 'BMP',
    'ICO': 'ICO'
}

IMAGE_QUALITY_SETTINGS = {
    'JPEG': {'quality': 92, 'optimize': True, 'progressive': True},
    'PNG': {'optimize': True, 'compress_level': 9},
    'WEBP': {'quality': 90, 'method': 6, 'lossless': False},
    'GIF': {'optimize': True},
    'TIFF': {'compression': 'tiff_lzw'},
    'BMP': {},
    'ICO': {'sizes': [(32, 32)]}
}

def get_mime_type(filename):
    return mimetypes.guess_type(filename)[0]

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS

def is_image_file(filename):
    mime = get_mime_type(filename)
    return mime and mime.startswith('image/')

def is_audio_file(filename):
    mime = get_mime_type(filename)
    return mime and mime.startswith('audio/')

def optimize_image(img, target_format):
    try:
        if target_format == 'JPEG':
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                img = background
            elif img.mode == 'P':
                img = img.convert('RGB')
            elif img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
        
        elif target_format == 'PNG':
            if img.mode not in ('RGBA', 'RGB', 'P'):
                img = img.convert('RGBA')
        
        elif target_format == 'WEBP':
            if img.mode not in ('RGBA', 'RGB'):
                img = img.convert('RGBA')
        
        elif target_format == 'GIF':
            if img.mode not in ('P', 'RGB', 'RGBA'):
                img = img.convert('RGB').convert('P', palette=Image.Palette.ADAPTIVE, colors=256)

        return img
    except Exception as e:
        logging.error(f'Fehler bei der Bildoptimierung: {str(e)}')
        raise

@app.route('/convert', methods=['POST'])
def convert_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei gefunden'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Keine Datei ausgewählt'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Nicht unterstütztes Dateiformat'}), 400

        # Temporäre Dateien erstellen
        temp_input = tempfile.NamedTemporaryFile(delete=False, dir=TEMP_DIR)
        file.save(temp_input.name)
        
        target_format = request.form.get('format', 'png').upper()
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{target_format.lower()}', dir=TEMP_DIR)

        try:
            if is_image_file(file.filename):
                if target_format not in FORMAT_MAPPING:
                    return jsonify({'error': 'Ungültiges Bildformat'}), 400

                with Image.open(temp_input.name) as img:
                    optimized_img = optimize_image(img, FORMAT_MAPPING[target_format])
                    save_params = IMAGE_QUALITY_SETTINGS.get(FORMAT_MAPPING[target_format], {}).copy()
                    optimized_img.save(temp_output.name, format=FORMAT_MAPPING[target_format], **save_params)

            elif is_audio_file(file.filename):
                if target_format.upper() not in ALLOWED_AUDIO_EXTENSIONS:
                    return jsonify({'error': 'Ungültiges Audioformat'}), 400

                audio = AudioSegment.from_file(temp_input.name)
                
                # Audio-Parameter verarbeiten
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
                
                # Audio exportieren
                export_params = {}
                if target_format.lower() == 'mp3':
                    bitrate = request.form.get('bitrate', '192k')
                    export_params['bitrate'] = bitrate
                
                audio.export(temp_output.name, format=target_format.lower(), **export_params)

            # Konvertierte Datei senden
            return send_file(
                temp_output.name,
                as_attachment=True,
                download_name=f"converted_{secure_filename(file.filename)}"
            )

        finally:
            # Temporäre Dateien aufräumen
            try:
                os.unlink(temp_input.name)
                os.unlink(temp_output.name)
            except:
                pass

    except Exception as e:
        logging.error(f'Fehler bei der Konvertierung: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return 'ShiftFile API is running'

@app.route('/formats')
def get_formats():
    return jsonify({
        'image': list(ALLOWED_IMAGE_EXTENSIONS),
        'audio': list(ALLOWED_AUDIO_EXTENSIONS)
    })

if __name__ == '__main__':
    mimetypes.init()
    app.run(debug=True, host='127.0.0.1', port=5000) 