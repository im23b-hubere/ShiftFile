document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const convertBtn = document.getElementById('convertBtn');
    const preview = document.getElementById('preview');
    const progress = document.getElementById('progress');
    const result = document.getElementById('result');
    const downloadLink = document.getElementById('downloadLink');
    const previewImage = document.getElementById('previewImage');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileFormat = document.getElementById('fileFormat');
    const convertTo = document.getElementById('convertTo');

    let selectedFile = null;

    // Drag and Drop Events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    function handleFile(file) {
        // Prüfe Dateityp
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/tiff', 'image/bmp', 'image/x-icon'];
        if (!allowedTypes.includes(file.type)) {
            alert('Bitte wählen Sie eine gültige Bilddatei aus.');
            return;
        }

        // Prüfe Dateigröße (10MB für Vercel)
        if (file.size > 10 * 1024 * 1024) {
            alert('Die Datei ist zu groß. Maximale Größe: 10MB');
            return;
        }

        selectedFile = file;
        showPreview(file);
        convertBtn.disabled = false;
    }

    function showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            fileName.textContent = file.name;
            fileSize.textContent = formatFileSize(file.size);
            fileFormat.textContent = file.type.split('/')[1].toUpperCase();
            preview.hidden = false;
        };
        reader.readAsDataURL(file);
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    convertBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const targetFormat = convertTo.value;
        
        // UI Updates
        convertBtn.disabled = true;
        progress.hidden = false;
        result.hidden = true;

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('format', targetFormat);

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                
                downloadLink.href = url;
                downloadLink.download = `converted_${selectedFile.name.split('.')[0]}.${targetFormat}`;
                
                result.hidden = false;
                progress.hidden = true;
            } else {
                const errorData = await response.json();
                alert(`Fehler: ${errorData.error || 'Unbekannter Fehler'}`);
                convertBtn.disabled = false;
                progress.hidden = true;
            }
        } catch (error) {
            console.error('Fehler:', error);
            alert('Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.');
            convertBtn.disabled = false;
            progress.hidden = true;
        }
    });

    // Reset functionality
    function resetUI() {
        selectedFile = null;
        preview.hidden = true;
        progress.hidden = true;
        result.hidden = true;
        convertBtn.disabled = true;
        fileInput.value = '';
    }

    // Add reset button functionality
    downloadLink.addEventListener('click', () => {
        setTimeout(resetUI, 1000);
    });
}); 