import os
from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image
import uuid
from datetime import datetime
import time
from werkzeug.utils import secure_filename
import logging
import sys
import atexit
import glob
import subprocess
from functools import lru_cache
import mimetypes
from pydub import AudioSegment
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
CONVERTED_DIR = os.path.join(BASE_DIR, 'converted')
LOG_FILE = os.path.join(BASE_DIR, 'conversion.log')
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_IMAGE_DIMENSION = 8000  # Maximale Bildgröße in Pixeln

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Erweiterte Dateiformat-Unterstützung
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'tiff', 'bmp', 'ico'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS.union(ALLOWED_AUDIO_EXTENSIONS)

# Optimierte Format-Zuordnung
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

# Audio-Format-Mapping für FFmpeg
AUDIO_FORMAT_MAPPING = {
    'MP3': {'codec': 'libmp3lame', 'ext': 'mp3'},
    'WAV': {'codec': 'pcm_s16le', 'ext': 'wav'},
    'OGG': {'codec': 'libvorbis', 'ext': 'ogg'},
    'FLAC': {'codec': 'flac', 'ext': 'flac'},
    'M4A': {'codec': 'aac', 'ext': 'm4a'},
    'AAC': {'codec': 'aac', 'ext': 'aac'}
}

# Optimierte Bildkonvertierung mit Qualitätseinstellungen
IMAGE_QUALITY_SETTINGS = {
    'JPEG': {'quality': 92, 'optimize': True, 'progressive': True},
    'PNG': {'optimize': True, 'compress_level': 9},
    'WEBP': {'quality': 90, 'method': 6, 'lossless': False},
    'GIF': {'optimize': True},
    'TIFF': {'compression': 'tiff_lzw'},
    'BMP': {},
    'ICO': {'sizes': [(32, 32)]}
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# Verzeichnisse erstellen
for directory in [FRONTEND_DIR, UPLOAD_DIR, CONVERTED_DIR]:
    os.makedirs(directory, exist_ok=True)
    logging.info(f'Verzeichnis bereit: {directory}')

@lru_cache(maxsize=1)
def get_ffmpeg_path():
    """Cache den FFmpeg-Pfad für bessere Performance"""
    ffmpeg_path = r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"
    if os.path.exists(ffmpeg_path):
        return ffmpeg_path
    return None

def get_mime_type(filename):
    """Ermittle den MIME-Typ einer Datei"""
    return mimetypes.guess_type(filename)[0]

def allowed_file(filename):
    """Überprüfe, ob die Dateiendung erlaubt ist"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS

def is_image_file(filename):
    """Überprüfe, ob es sich um eine Bilddatei handelt"""
    mime = get_mime_type(filename)
    return mime and mime.startswith('image/')

def is_audio_file(filename):
    """Überprüfe, ob es sich um eine Audiodatei handelt"""
    mime = get_mime_type(filename)
    return mime and mime.startswith('audio/')

def optimize_image(img, target_format):
    """Optimiere ein Bild für die Konvertierung"""
    try:
        # Größenbeschränkung prüfen
        if max(img.size) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Format-spezifische Optimierungen
        if target_format == 'JPEG':
            if img.mode in ('RGBA', 'LA'):
                # Bessere Behandlung von transparenten Bildern
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

def convert_audio(input_path, output_path, target_format):
    """Konvertiere Audiodateien mit FFmpeg"""
    try:
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            raise Exception("FFmpeg nicht gefunden")

        # Audio-Parameter sammeln
        audio_params = {
            'volume': request.form.get('volume', '0'),
            'speed': request.form.get('speed', '1.0'),
            'fade_in': request.form.get('fade_in', '0'),
            'fade_out': request.form.get('fade_out', '0'),
            'normalize': request.form.get('normalize', 'false').lower() == 'true',
            'mono': request.form.get('mono', 'false').lower() == 'true',
            'bitrate': request.form.get('bitrate', '192k')
        }

        # FFmpeg-Befehl erstellen
        command = [ffmpeg_path, '-y', '-i', input_path]
        filters = []

        # Audio-Filter hinzufügen
        if float(audio_params['volume']) != 0:
            filters.append(f"volume={audio_params['volume']}dB")
        
        if float(audio_params['speed']) != 1.0:
            filters.append(f"atempo={audio_params['speed']}")
        
        if audio_params['normalize']:
            filters.append('loudnorm=I=-16:TP=-1.5:LRA=11')  # Verbesserte Normalisierung
        
        if float(audio_params['fade_in']) > 0:
            filters.append(f"afade=t=in:st=0:d={audio_params['fade_in']}")
        
        if float(audio_params['fade_out']) > 0:
            duration_cmd = [ffmpeg_path, '-i', input_path, '-show_entries', 
                          'format=duration', '-v', 'quiet', '-of', 'csv=p=0']
            duration = float(subprocess.check_output(duration_cmd).decode().strip())
            filters.append(f"afade=t=out:st={duration-float(audio_params['fade_out'])}:d={audio_params['fade_out']}")
        
        if audio_params['mono']:
            filters.append('pan=mono|c0=.5*c0+.5*c1')

        # Filter zum Befehl hinzufügen
        if filters:
            command.extend(['-af', ','.join(filters)])

        # Format-spezifische Einstellungen
        format_settings = AUDIO_FORMAT_MAPPING.get(target_format.upper())
        if not format_settings:
            raise ValueError(f"Nicht unterstütztes Audioformat: {target_format}")

        command.extend(['-acodec', format_settings['codec']])
        
        # Bitrate nur für verlustbehaftete Formate
        if format_settings['codec'] in ['libmp3lame', 'aac', 'libvorbis']:
            command.extend(['-ab', audio_params['bitrate']])

        command.append(output_path)
        
        # Befehl ausführen
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            logging.error(f'FFmpeg Fehler: {result.stderr}')
            return False
        
        return True
    except Exception as e:
        logging.error(f'Fehler bei der Audio-Konvertierung: {str(e)}')
        return False

def clean_old_files(max_age=3600):
    """Lösche alte temporäre Dateien"""
    try:
        current_time = time.time()
        for folder in [UPLOAD_DIR, CONVERTED_DIR]:
            for f in glob.glob(os.path.join(folder, '*')):
                if os.path.isfile(f):
                    file_time = os.path.getmtime(f)
                    if current_time - file_time > max_age:
                        try:
                            os.remove(f)
                            logging.info(f'Alte Datei gelöscht: {f}')
                        except Exception as e:
                            logging.warning(f'Konnte Datei nicht löschen: {f} - {str(e)}')
    except Exception as e:
        logging.error(f'Fehler beim Bereinigen der temporären Dateien: {str(e)}')

@app.route('/')
def index():
    """Hauptseite"""
    return app.send_static_file('index.html')

@app.route('/formats')
def get_formats():
    """API-Endpoint für verfügbare Formate"""
    return jsonify({
        'image': list(ALLOWED_IMAGE_EXTENSIONS),
        'audio': list(ALLOWED_AUDIO_EXTENSIONS)
    })

@app.route('/convert', methods=['POST'])
def convert_file():
    """Datei-Konvertierungs-Endpoint"""
    try:
        # Request validieren
        if 'file' not in request.files:
            return 'Keine Datei gefunden', 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return 'Keine Datei ausgewählt', 400
        
        if not allowed_file(file.filename):
            return 'Nicht unterstütztes Dateiformat', 400

        # Dateigröße prüfen
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            return 'Datei zu groß (Max 100MB)', 400

        # Sichere Dateinamen generieren
        input_filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        input_path = os.path.join(UPLOAD_DIR, input_filename)
        
        target_format = request.form.get('format', 'png').upper()
        output_filename = f"converted_{uuid.uuid4()}.{target_format.lower()}"
        output_path = os.path.join(CONVERTED_DIR, output_filename)

        # Upload speichern
        file.save(input_path)

        try:
            # Konvertierung basierend auf Dateityp
            if is_image_file(file.filename):
                if target_format not in FORMAT_MAPPING:
                    return 'Ungültiges Bildformat', 400

                with Image.open(input_path) as img:
                    try:
                        # Bild optimieren
                        optimized_img = optimize_image(img, FORMAT_MAPPING[target_format])
                        
                        # Mit optimierten Einstellungen speichern
                        save_params = IMAGE_QUALITY_SETTINGS.get(FORMAT_MAPPING[target_format], {}).copy()
                        
                        # Spezielle Behandlung für ICO-Format
                        if FORMAT_MAPPING[target_format] == 'ICO':
                            optimized_img.save(output_path, format=FORMAT_MAPPING[target_format], **save_params)
                        else:
                            optimized_img.save(output_path, format=FORMAT_MAPPING[target_format], **save_params)
                            
                    except Exception as e:
                        logging.error(f'Fehler bei der Bildkonvertierung: {str(e)}')
                        return f'Fehler bei der Bildkonvertierung: {str(e)}', 500

            elif is_audio_file(file.filename):
                if target_format.upper() not in AUDIO_FORMAT_MAPPING:
                    return 'Ungültiges Audioformat', 400

                if not convert_audio(input_path, output_path, target_format):
                    return 'Fehler bei der Audio-Konvertierung', 500

            # Upload löschen
            os.remove(input_path)

            # Konvertierte Datei senden
            return send_file(
                output_path,
                as_attachment=True,
                download_name=f"converted_{os.path.splitext(file.filename)[0]}.{target_format.lower()}"
            )

        finally:
            # Aufräumen bei Fehlern
            if os.path.exists(input_path):
                os.remove(input_path)

    except Exception as e:
        logging.error(f'Fehler bei der Konvertierung: {str(e)}')
        return str(e), 500

@app.route('/api/process-audio', methods=['POST'])
def process_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Kein Dateiname angegeben'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Nicht unterstütztes Dateiformat'}), 400

    try:
        # Temporäre Datei erstellen
        temp_input = tempfile.NamedTemporaryFile(delete=False)
        file.save(temp_input.name)
        
        # Audio laden
        audio = AudioSegment.from_file(temp_input.name)
        
        # Audio-Parameter aus der Anfrage
        volume_db = float(request.form.get('volume', 0))
        speed = float(request.form.get('speed', 1.0))
        fade_in = int(request.form.get('fadeIn', 0))
        fade_out = int(request.form.get('fadeOut', 0))
        normalize = request.form.get('normalize', 'false').lower() == 'true'
        mono = request.form.get('mono', 'false').lower() == 'true'
        output_format = request.form.get('format', 'mp3')
        
        # Audio-Verarbeitung
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
        
        # Temporäre Ausgabedatei erstellen
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{output_format}')
        
        # Audio exportieren
        export_params = {}
        if output_format == 'mp3':
            bitrate = request.form.get('bitrate', '192k')
            export_params['bitrate'] = bitrate
        
        audio.export(temp_output.name, format=output_format, **export_params)
        
        # Verarbeitete Datei zurücksenden
        return send_file(
            temp_output.name,
            as_attachment=True,
            download_name=f"processed_{secure_filename(file.filename)}"
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # Temporäre Dateien aufräumen
        try:
            os.unlink(temp_input.name)
            os.unlink(temp_output.name)
        except:
            pass

if __name__ == '__main__':
    # Alte Dateien beim Start bereinigen
    clean_old_files()
    
    # Bereinigungs-Task registrieren
    atexit.register(clean_old_files)
    
    # MIME-Typen initialisieren
    mimetypes.init()
    
    # Server starten
    logging.info('Server gestartet')
    print('Server wird gestartet...')
    print(f'Frontend-Verzeichnis: {FRONTEND_DIR}')
    print('Öffnen Sie http://127.0.0.1:5000 in Ihrem Browser')
    
    app.run(
        debug=True,
        host='127.0.0.1',
        port=5000,
        use_reloader=True
    ) 