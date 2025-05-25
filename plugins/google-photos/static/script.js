let currentBatch = [];
let currentIndex = 0;
let currentAlbum = "";
let progressIntervalId = null;

function startProgressBar() {
    if (progressIntervalId) {
        clearInterval(progressIntervalId);
    }

    let timePassed = 0;
    const progressEl = document.getElementById('photo-progress');
    if (progressEl) {
        progressEl.style.width = '100%';
    }

    progressIntervalId = setInterval(() => {
        timePassed++;
        const percentLeft = 100 - (timePassed / 30) * 100; // 30 seconds per photo
        if (progressEl) {
            progressEl.style.width = percentLeft + '%';
        }

        if (timePassed >= 30) {
            clearInterval(progressIntervalId);
            nextMedia();
        }
    }, 1000);
}

function showMedia(mediaItem) {
    const container = document.getElementById('photo-container');
    if (!container) return;

    // Clear previous content
    container.innerHTML = '';

    if (mediaItem.error) {
        container.innerHTML = `<div class="error-message">${mediaItem.error}</div>`;
        return;
    }

    // Create progress bar
    const progressBar = document.createElement('div');
    progressBar.id = 'photo-progress';
    progressBar.className = 'photo-progress';
    container.appendChild(progressBar);

    // Create media element
    let mediaElement;
    if (mediaItem.mediaType === 'video') {
        mediaElement = document.createElement('video');
        mediaElement.autoplay = true;
        mediaElement.loop = true;
        mediaElement.muted = true;
        mediaElement.controls = false;
    } else {
        mediaElement = document.createElement('img');
    }

    // Set source and load
    mediaElement.src = mediaItem.baseUrl;
    mediaElement.onload = () => {
        container.appendChild(mediaElement);
        startProgressBar();
    };

    // Show album title
    const infoDiv = document.createElement('div');
    infoDiv.className = 'photo-info';
    infoDiv.textContent = currentAlbum;
    container.appendChild(infoDiv);
}

function nextMedia() {
    if (currentBatch.length === 0) {
        updatePhotoBatch();
        return;
    }

    currentIndex = (currentIndex + 1) % currentBatch.length;
    showMedia(currentBatch[currentIndex]);
}

function updatePhotoBatch() {
    fetch('/api/plugins/google-photos/data')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error:", data.error);
                return;
            }
            currentBatch = data.photos;
            currentAlbum = data.album_title;
            currentIndex = 0;
            if (currentBatch.length > 0) {
                showMedia(currentBatch[0]);
            }
        })
        .catch(error => console.error('Error fetching new photo batch:', error));
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updatePhotoBatch();
}); 