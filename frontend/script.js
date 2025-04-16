document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const convertBtn = document.getElementById('convertBtn');
    const progress = document.getElementById('progress');
    const progressBar = progress.querySelector('.progress-bar');
    const result = document.getElementById('result');
    const downloadLink = document.getElementById('downloadLink');
    const convertTo = document.getElementById('convertTo');
    const convertToAudio = document.getElementById('convertToAudio');
    const preview = document.getElementById('preview');
    const previewImage = document.getElementById('previewImage');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const fileFormat = document.getElementById('fileFormat');
    const formatBtns = document.querySelectorAll('.format-btn');

    let currentFileType = 'image';

    formatBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            formatBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFileType = btn.dataset.type;
            
            if (currentFileType === 'image') {
                convertTo.hidden = false;
                convertToAudio.hidden = true;
                fileInput.accept = '.jpg,.jpeg,.png,.webp,.gif,.tiff';
            } else {
                convertTo.hidden = true;
                convertToAudio.hidden = false;
                fileInput.accept = '.mp3,.wav';
            }

            preview.hidden = true;
            result.hidden = true;
            convertBtn.disabled = true;
        });
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            const fileType = file.type.split('/')[0];
            
            if ((currentFileType === 'image' && fileType === 'image') ||
                (currentFileType === 'audio' && fileType === 'audio')) {
                
                if (fileType === 'image') {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        previewImage.src = e.target.result;
                        preview.hidden = false;
                    };
                    reader.readAsDataURL(file);
                } else {
                    preview.hidden = true;
                }

                fileName.textContent = file.name;
                fileSize.textContent = formatFileSize(file.size);
                fileFormat.textContent = file.type.split('/')[1].toUpperCase();
                convertBtn.disabled = false;
                result.hidden = true;
                convertBtn.onclick = () => convertFile(file);
            } else {
                alert(`Bitte wählen Sie eine ${currentFileType === 'image' ? 'Bilddatei' : 'Audiodatei'} aus`);
            }
        }
    }

    async function convertFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', currentFileType === 'image' ? convertTo.value : convertToAudio.value);

        progress.hidden = false;
        result.hidden = true;
        convertBtn.disabled = true;
        progressBar.style.width = '0%';

        try {
            progressBar.style.width = '50%';
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                downloadLink.href = url;
                downloadLink.download = `converted.${currentFileType === 'image' ? convertTo.value : convertToAudio.value}`;
                progressBar.style.width = '100%';
                result.hidden = false;
            } else {
                const errorText = await response.text();
                throw new Error(errorText);
            }
        } catch (error) {
            alert('Fehler bei der Konvertierung: ' + error.message);
        } finally {
            convertBtn.disabled = false;
            setTimeout(() => {
                progress.hidden = true;
                progressBar.style.width = '0%';
            }, 1000);
        }
    }
}); 