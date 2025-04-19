import os
import requests
from PIL import Image
import io
import logging
import unittest
from app import app, TEMP_DIR
from werkzeug.datastructures import FileStorage

SERVER_URL = "http://127.0.0.1:5000"
TEST_DIR = "test_files"

if not os.path.exists(TEST_DIR):
    os.makedirs(TEST_DIR)

def test_image_conversion():
    """Teste Bildkonvertierung"""
    print("\nTeste Bildkonvertierung...")
    
    test_image = Image.new('RGB', (100, 100), color='red')
    test_image_path = os.path.join(TEST_DIR, 'test.png')
    test_image.save(test_image_path)
    
    with open(test_image_path, 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        data = {'format': 'jpg'}
        response = requests.post(f"{SERVER_URL}/convert", files=files, data=data)
        
        if response.status_code == 200:
            print("✓ PNG zu JPG Konvertierung erfolgreich")
        else:
            print(f"✗ PNG zu JPG Konvertierung fehlgeschlagen: {response.text}")

def test_audio_conversion():
    """Teste Audiokonvertierung"""
    print("\nTeste Audiokonvertierung...")
    
    test_audio_path = os.path.join(TEST_DIR, 'test.wav')
    os.system(f'ffmpeg -f lavfi -i "sine=frequency=1000:duration=5" -c:a pcm_s16le {test_audio_path}')
    
    # Test WAV zu MP3
    with open(test_audio_path, 'rb') as f:
        files = {'file': ('test.wav', f, 'audio/wav')}
        data = {
            'format': 'mp3',
            'volume': '0',
            'speed': '1.0',
            'normalize': 'false',
            'mono': 'false'
        }
        response = requests.post(f"{SERVER_URL}/convert", files=files, data=data)
        
        if response.status_code == 200:
            print("✓ WAV zu MP3 Konvertierung erfolgreich")
        else:
            print(f"✗ WAV zu MP3 Konvertierung fehlgeschlagen: {response.text}")

def test_formats_endpoint():
    """Teste Formats-Endpoint"""
    print("\nTeste Formats-Endpoint...")
    
    response = requests.get(f"{SERVER_URL}/formats")
    if response.status_code == 200:
        formats = response.json()
        if 'image' in formats and 'audio' in formats:
            print("✓ Formats-Endpoint funktioniert")
            print(f"  Unterstützte Bildformate: {', '.join(formats['image'])}")
            print(f"  Unterstützte Audioformate: {', '.join(formats['audio'])}")
        else:
            print("✗ Formats-Endpoint: Ungültiges Format")
    else:
        print(f"✗ Formats-Endpoint fehlgeschlagen: {response.text}")

class TestImageConverter(unittest.TestCase):
    def setUp(self):
        # Erstelle Testverzeichnis, falls es nicht existiert
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # Erstelle ein Testbild
        self.test_image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        self.test_image_buffer = io.BytesIO()
        self.test_image.save(self.test_image_buffer, format='PNG')
        self.test_image_buffer.seek(0)
        
        # Erstelle Flask Test Client
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        # Aufräumen nach den Tests
        for file in os.listdir(TEMP_DIR):
            if file.startswith(("input_", "output_", "test_")):
                try:
                    os.remove(os.path.join(TEMP_DIR, file))
                except Exception as e:
                    print(f"Fehler beim Löschen von {file}: {e}")

    def test_png_to_jpg_conversion(self):
        """Test PNG zu JPG Konvertierung mit Transparenz"""
        data = {}
        data['format'] = 'jpg'
        data['file'] = (self.test_image_buffer, 'test.png')
        
        response = self.client.post('/api/convert',
                                  data=data,
                                  content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        
        # Speichere die Antwort temporär und überprüfe sie
        output_path = os.path.join(TEMP_DIR, "test_output.jpg")
        with open(output_path, 'wb') as f:
            f.write(response.data)
        
        # Überprüfe, ob die konvertierte Datei ein gültiges JPG ist
        converted_img = Image.open(output_path)
        self.assertEqual(converted_img.format, "JPEG")
        self.assertEqual(converted_img.mode, "RGB")

    def test_png_optimization(self):
        """Test der PNG-Optimierung"""
        data = {}
        data['format'] = 'png'
        data['file'] = (self.test_image_buffer, 'test.png')
        
        response = self.client.post('/api/convert',
                                  data=data,
                                  content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        
        # Speichere die Antwort temporär und überprüfe sie
        output_path = os.path.join(TEMP_DIR, "test_output.png")
        with open(output_path, 'wb') as f:
            f.write(response.data)
        
        # Überprüfe, ob die optimierte Datei ein gültiges PNG ist
        optimized_img = Image.open(output_path)
        self.assertEqual(optimized_img.format, "PNG")
        self.assertEqual(optimized_img.mode, "RGBA")

    def test_invalid_format(self):
        """Test mit ungültigem Zielformat"""
        data = {}
        data['format'] = 'invalid_format'
        data['file'] = (self.test_image_buffer, 'test.png')
        
        response = self.client.post('/api/convert',
                                  data=data,
                                  content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Nicht unterstütztes Zielformat', response.json['error'])

    def test_missing_format(self):
        """Test ohne Angabe des Zielformats"""
        data = {}
        data['file'] = (self.test_image_buffer, 'test.png')
        
        response = self.client.post('/api/convert',
                                  data=data,
                                  content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Zielformat nicht angegeben', response.json['error'])

    def test_invalid_source_format(self):
        """Test mit ungültigem Quellformat"""
        data = {}
        data['format'] = 'jpg'
        
        # Erstelle eine Testdatei mit ungültigem Format
        test_file = io.BytesIO(b'Invalid file content')
        data['file'] = (test_file, 'test.xyz')
        
        response = self.client.post('/api/convert',
                                  data=data,
                                  content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Nicht unterstütztes Dateiformat', response.json['error'])

if __name__ == "__main__":
    print("Starte Tests...")
    
    try:
        # Teste Formats-Endpoint
        test_formats_endpoint()
        
        # Teste Bildkonvertierung
        test_image_conversion()
        
        # Teste Audiokonvertierung
        test_audio_conversion()
        
    except Exception as e:
        print(f"\n✗ Test fehlgeschlagen: {str(e)}")
    
    print("\nTests abgeschlossen.")

    unittest.main() 