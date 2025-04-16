document.addEventListener('DOMContentLoaded', () => {
    const elements = {
        dropZone: document.getElementById('dropZone'),
        fileInput: document.getElementById('fileInput'),
        convertBtn: document.getElementById('convertBtn'),
        progress: document.getElementById('progress'),
        progressBar: document.getElementById('progress').querySelector('.progress-bar'),
        result: document.getElementById('result'),
        downloadLink: document.getElementById('downloadLink'),
        convertTo: document.getElementById('convertTo'),
        convertToAudio: document.getElementById('convertToAudio'),
        preview: document.getElementById('preview'),
        previewImage: document.getElementById('previewImage'),
        fileName: document.getElementById('fileName'),
        fileSize: document.getElementById('fileSize'),
        fileFormat: document.getElementById('fileFormat')
    };

    let currentFileType = 'image';
    let currentFile = null;
    let audioControls = null;

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    const FILE_SIZES = ['Bytes', 'KB', 'MB', 'GB'];
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${FILE_SIZES[i]}`;
    }

    document.querySelector('.format-selector').addEventListener('click', (e) => {
        const btn = e.target.closest('.format-btn');
        if (!btn) return;

        document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFileType = btn.dataset.type;
        
        elements.previewImage.src = '';
        elements.previewImage.style.display = currentFileType === 'image' ? 'block' : 'none';
        elements.preview.hidden = true;
        elements.result.hidden = true;
        elements.convertBtn.disabled = true;
        
        if (currentFileType === 'image') {
            elements.convertTo.hidden = false;
            elements.convertToAudio.hidden = true;
            elements.fileInput.accept = '.jpg,.jpeg,.png,.webp,.gif,.tiff';
            document.querySelector('.audio-controls')?.style.setProperty('display', 'none');
        } else {
            elements.convertTo.hidden = true;
            elements.convertToAudio.hidden = false;
            elements.fileInput.accept = '.mp3,.wav,.ogg,.flac,.m4a,.aac';
        }
    });

    const dragEvents = ['dragover', 'dragleave', 'drop'];
    dragEvents.forEach(eventName => {
        elements.dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (eventName === 'dragover') {
                elements.dropZone.classList.add('dragover');
            } else if (eventName === 'dragleave' || eventName === 'drop') {
                elements.dropZone.classList.remove('dragover');
                if (eventName === 'drop') {
                    handleFiles(e.dataTransfer.files);
                }
            }
        });
    });

    elements.dropZone.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    function createAudioControls() {
        if (audioControls) return audioControls;

        audioControls = document.createElement('div');
        audioControls.className = 'audio-controls';
        audioControls.innerHTML = `
            <div class="control-group">
                <label>Lautstärke (dB): <span id="volumeValue">0</span></label>
                <input type="range" id="volume" min="-20" max="20" value="0" step="1">
            </div>
            <div class="control-group">
                <label>Geschwindigkeit: <span id="speedValue">1.0</span>x</label>
                <input type="range" id="speed" min="0.5" max="2" value="1.0" step="0.1">
            </div>
            <div class="control-group">
                <label>Fade-In (Sekunden):</label>
                <input type="number" id="fadeIn" min="0" max="10" value="0" step="0.1">
            </div>
            <div class="control-group">
                <label>Fade-Out (Sekunden):</label>
                <input type="number" id="fadeOut" min="0" max="10" value="0" step="0.1">
            </div>
            <div class="control-group">
                <label>
                    <input type="checkbox" id="normalize">
                    Lautstärke normalisieren
                </label>
            </div>
            <div class="control-group">
                <label>
                    <input type="checkbox" id="mono">
                    Zu Mono konvertieren
                </label>
            </div>
            <div class="control-group mp3-only" style="display: none;">
                <label>MP3 Bitrate:</label>
                <select id="bitrate">
                    <option value="128k">128 kbps</option>
                    <option value="192k" selected>192 kbps</option>
                    <option value="256k">256 kbps</option>
                    <option value="320k">320 kbps</option>
                </select>
            </div>
        `;
        
        document.querySelector('.preview-container').insertAdjacentElement('afterend', audioControls);
        
        const updateValue = debounce((id, value) => {
            document.getElementById(`${id}Value`).textContent = value;
        }, 50);

        audioControls.querySelector('#volume').addEventListener('input', (e) => updateValue('volume', e.target.value));
        audioControls.querySelector('#speed').addEventListener('input', (e) => updateValue('speed', e.target.value));

        return audioControls;
    }

    function handleFiles(files) {
        if (!files.length) return;

        const file = files[0];
        const fileType = file.type.split('/')[0];
        
        if ((currentFileType === 'image' && fileType === 'image') ||
            (currentFileType === 'audio' && fileType === 'audio')) {
            
            if (fileType === 'image') {
                const reader = new FileReader();
                reader.onload = (e) => {
                    elements.previewImage.src = e.target.result;
                    elements.preview.hidden = false;
                    document.querySelector('.audio-controls')?.style.setProperty('display', 'none');
                };
                reader.readAsDataURL(file);
            } else {
                elements.previewImage.src = '';
                elements.preview.hidden = false;
                elements.previewImage.style.display = 'none';
                
                let audioControls = document.querySelector('.audio-controls');
                if (!audioControls) {
                    createAudioControls();
                    audioControls = document.querySelector('.audio-controls');
                }
                audioControls.style.display = 'block';
            }

            elements.fileName.textContent = file.name;
            elements.fileSize.textContent = formatFileSize(file.size);
            elements.fileFormat.textContent = file.type.split('/')[1].toUpperCase();
            elements.convertBtn.disabled = false;
            elements.result.hidden = true;
            elements.convertBtn.onclick = () => convertFile(file);
        } else {
            alert(`Bitte wählen Sie eine ${currentFileType === 'image' ? 'Bilddatei' : 'Audiodatei'} aus`);
        }
    }

    async function convertFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', currentFileType === 'image' ? elements.convertTo.value : elements.convertToAudio.value);

        if (file.type.startsWith('audio/')) {
            const audioSettings = {
                volume: document.getElementById('volume').value,
                speed: document.getElementById('speed').value,
                fadeIn: document.getElementById('fadeIn').value,
                fadeOut: document.getElementById('fadeOut').value,
                normalize: document.getElementById('normalize').checked,
                mono: document.getElementById('mono').checked,
                bitrate: document.getElementById('bitrate')?.value || '192k'
            };

            Object.entries(audioSettings).forEach(([key, value]) => {
                formData.append(key, value);
            });
        }

        elements.progress.hidden = false;
        elements.result.hidden = true;
        elements.convertBtn.disabled = true;
        elements.progressBar.style.width = '0%';

        try {
            elements.progressBar.style.width = '50%';
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                elements.downloadLink.href = url;
                elements.downloadLink.download = `converted_${file.name.split('.')[0]}.${
                    currentFileType === 'image' ? elements.convertTo.value : elements.convertToAudio.value
                }`;
                elements.progressBar.style.width = '100%';
                elements.result.hidden = false;
            } else {
                const errorText = await response.text();
                throw new Error(errorText);
            }
        } catch (error) {
            alert('Fehler bei der Konvertierung: ' + error.message);
        } finally {
            elements.convertBtn.disabled = false;
            setTimeout(() => {
                elements.progress.hidden = true;
                elements.progressBar.style.width = '0%';
            }, 1000);
        }
    }

    const style = document.createElement('style');
    style.textContent = `
        .audio-controls {
            margin: 20px;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
            background-color: #f9f9f9;
            display: none;
        }
        .control-group {
            margin-bottom: 15px;
        }
        .control-group label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        .control-group input[type="range"] {
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
        }
        .control-group input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            background: #4CAF50;
            border-radius: 50%;
            cursor: pointer;
        }
        .control-group input[type="number"] {
            width: 80px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .control-group select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #fff;
        }
        .mp3-only {
            padding-top: 10px;
            border-top: 1px solid #ddd;
        }
        .process-button {
            display: block;
            width: 100%;
            padding: 10px;
            margin-top: 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }
        .process-button:hover {
            background-color: #45a049;
        }
        .process-button:active {
            background-color: #3d8b40;
        }
    `;
    document.head.appendChild(style);

    async function processAudio() {
        const fileInput = document.querySelector('input[type="file"]');
        if (!fileInput.files.length) {
            alert('Bitte wählen Sie eine Datei aus');
            return;
        }

        const file = fileInput.files[0];
        if (!file.type.startsWith('audio/')) {
            alert('Bitte wählen Sie eine gültige Audiodatei aus');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        const audioParams = {
            volume: document.getElementById('volume')?.value || '0',
            speed: document.getElementById('speed')?.value || '1.0',
            fadeIn: document.getElementById('fadeIn')?.value || '0',
            fadeOut: document.getElementById('fadeOut')?.value || '0',
            normalize: document.getElementById('normalize')?.checked || false,
            mono: document.getElementById('mono')?.checked || false,
            format: document.getElementById('convertToAudio')?.value || 'mp3',
            bitrate: document.getElementById('bitrate')?.value || '192k'
        };

        Object.entries(audioParams).forEach(([key, value]) => {
            formData.append(key, value);
        });

        try {
            elements.progress.hidden = false;
            elements.progressBar.style.width = '50%';
            
            const response = await fetch('/api/process-audio', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Fehler bei der Audio-Verarbeitung');
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            elements.downloadLink.href = url;
            elements.downloadLink.download = `processed_${file.name}`;
            elements.progressBar.style.width = '100%';
            elements.result.hidden = false;

        } catch (error) {
            alert(`Fehler: ${error.message}`);
            console.error('Audio-Verarbeitungsfehler:', error);
        } finally {
            setTimeout(() => {
                elements.progress.hidden = true;
                elements.progressBar.style.width = '0%';
            }, 1000);
        }
    }

    function addProcessButton() {
        const controls = document.querySelector('.controls');
        if (!controls) return;

        const processButton = document.createElement('button');
        processButton.textContent = 'Audio verarbeiten';
        processButton.className = 'process-button';
        processButton.onclick = processAudio;
        controls.appendChild(processButton);
    }

    createAudioControls();
    addProcessButton();
}); 