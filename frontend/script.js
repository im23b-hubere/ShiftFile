// Aktualisiere die API-Endpunkte
const API_ENDPOINTS = {
    FORMATS: '/api/formats',
    CONVERT: '/api/convert'
};

document.addEventListener('DOMContentLoaded', () => {
    const elements = {
        dropZone: document.getElementById('dropZone'),
        fileInput: document.getElementById('fileInput'),
        convertBtn: document.getElementById('convertBtn'),
        progress: document.getElementById('progress'),
        progressBar: document.getElementById('progress').querySelector('.progress-bar'),
        result: document.getElementById('result'),
        downloadLink: document.getElementById('downloadLink'),
        preview: document.getElementById('preview'),
        previewImage: document.getElementById('previewImage'),
        fileName: document.getElementById('fileName'),
        fileSize: document.getElementById('fileSize'),
        fileFormat: document.getElementById('fileFormat'),
        format: document.getElementById('format')
    };

    let currentFileType = 'image';
    let currentFile = null;

    const FILE_SIZES = ['Bytes', 'KB', 'MB', 'GB'];
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${FILE_SIZES[i]}`;
    }

    function createAudioControls() {
        const controls = document.createElement('div');
        controls.id = 'audioControls';
        controls.className = 'audio-controls';
        controls.innerHTML = `
            <div class="control-group">
                <label for="volume">Lautstärke (dB): <span id="volumeValue">0</span></label>
                <input type="range" id="volume" min="-20" max="20" value="0" step="1">
            </div>
            <div class="control-group">
                <label for="speed">Geschwindigkeit: <span id="speedValue">1.0</span>x</label>
                <input type="range" id="speed" min="0.5" max="2" value="1.0" step="0.1">
            </div>
            <div class="control-group">
                <label for="fadeIn">Fade-In (Sekunden)</label>
                <input type="number" id="fadeIn" min="0" max="10" value="0" step="1">
            </div>
            <div class="control-group">
                <label for="fadeOut">Fade-Out (Sekunden)</label>
                <input type="number" id="fadeOut" min="0" max="10" value="0" step="1">
            </div>
            <div class="control-group">
                <label>
                    <input type="checkbox" id="normalize">
                    Normalisieren
                </label>
            </div>
            <div class="control-group">
                <label>
                    <input type="checkbox" id="mono">
                    Mono
                </label>
            </div>
            <div class="control-group" id="bitrateContainer" style="display: none;">
                <label for="bitrate">MP3 Bitrate</label>
                <select id="bitrate">
                    <option value="128">128 kbps</option>
                    <option value="192" selected>192 kbps</option>
                    <option value="256">256 kbps</option>
                    <option value="320">320 kbps</option>
                </select>
            </div>
        `;

        const previewContainer = document.querySelector('.preview-container');
        if (previewContainer) {
            previewContainer.parentNode.insertBefore(controls, previewContainer.nextSibling);
        }

        // Event-Listener für Live-Updates der Werte
        document.getElementById('volume').addEventListener('input', function() {
            document.getElementById('volumeValue').textContent = this.value;
        });

        document.getElementById('speed').addEventListener('input', function() {
            document.getElementById('speedValue').textContent = this.value;
        });

        return controls;
    }

    // Drag & Drop Funktionalität
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        elements.dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (eventName === 'dragenter' || eventName === 'dragover') {
                elements.dropZone.classList.add('dragover');
            } else {
                elements.dropZone.classList.remove('dragover');
                if (eventName === 'drop') {
                    handleFiles(e.dataTransfer.files);
                }
            }
        });
    });

    elements.dropZone.addEventListener('click', () => elements.fileInput.click());

    async function convertFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', elements.format.value);

        if (currentFileType === 'audio') {
            formData.append('volume', document.getElementById('volume').value);
            formData.append('speed', document.getElementById('speed').value);
            formData.append('fadeIn', document.getElementById('fadeIn').value);
            formData.append('fadeOut', document.getElementById('fadeOut').value);
            formData.append('normalize', document.getElementById('normalize').checked);
            formData.append('mono', document.getElementById('mono').checked);
            
            if (elements.format.value === 'mp3') {
                formData.append('bitrate', document.getElementById('bitrate').value);
            }
        }

        elements.progress.hidden = false;
        elements.progressBar.style.width = '50%';

        try {
            const response = await fetch(API_ENDPOINTS.CONVERT, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Konvertierung fehlgeschlagen');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            elements.downloadLink.href = url;
            elements.downloadLink.download = `converted_${file.name}`;
            elements.progressBar.style.width = '100%';
            elements.result.hidden = false;

        } catch (error) {
            alert('Fehler bei der Konvertierung: ' + error.message);
            console.error('Error:', error);
        } finally {
            setTimeout(() => {
                elements.progress.hidden = true;
                elements.progressBar.style.width = '0%';
            }, 1000);
        }
    }

    function handleFiles(files) {
        if (!files.length) return;

        const file = files[0];
        currentFile = file;
        
        // Dateivorschau
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                elements.previewImage.src = e.target.result;
                elements.previewImage.style.display = 'block';
                elements.preview.hidden = false;
            };
            reader.readAsDataURL(file);
            
            // Verstecke Audio-Controls
            const audioControls = document.getElementById('audioControls');
            if (audioControls) audioControls.style.display = 'none';
            currentFileType = 'image';
        } else if (file.type.startsWith('audio/')) {
            elements.previewImage.style.display = 'none';
            elements.preview.hidden = false;
            
            // Zeige Audio-Controls
            let audioControls = document.getElementById('audioControls');
            if (!audioControls) {
                audioControls = createAudioControls();
            }
            audioControls.style.display = 'block';
            currentFileType = 'audio';
        }

        // Aktualisiere Dateiinformationen
        elements.fileName.textContent = file.name;
        elements.fileSize.textContent = formatFileSize(file.size);
        elements.fileFormat.textContent = file.type.split('/')[1].toUpperCase();
        elements.result.hidden = true;
    }

    // Hole unterstützte Formate vom Server
    fetch(API_ENDPOINTS.FORMATS)
        .then(response => response.json())
        .then(data => {
            elements.fileInput.addEventListener('change', function(e) {
                handleFiles(this.files);
                
                const file = this.files[0];
                if (file) {
                    const extension = file.name.split('.').pop().toLowerCase();
                    
                    // Setze die verfügbaren Zielformate
                    elements.format.innerHTML = '';
                    const formats = file.type.startsWith('image/') ? data.image : data.audio;
                    formats.forEach(format => {
                        const option = document.createElement('option');
                        option.value = format;
                        option.textContent = format.toUpperCase();
                        elements.format.appendChild(option);
                    });
                }
            });

            // Event-Listener für Format-Änderung
            elements.format.addEventListener('change', function() {
                const bitrateContainer = document.getElementById('bitrateContainer');
                if (bitrateContainer) {
                    bitrateContainer.style.display = this.value === 'mp3' ? 'block' : 'none';
                }
            });
        })
        .catch(error => {
            console.error('Error fetching formats:', error);
            alert('Fehler beim Laden der unterstützten Formate');
        });

    // Event-Listener für den Konvertierungsbutton
    elements.convertBtn.addEventListener('click', () => {
        if (currentFile) {
            convertFile(currentFile);
        }
    });
}); 