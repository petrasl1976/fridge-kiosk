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
    if (!container) {
        console.error('[Google Photos] photo-container not found in DOM');
        return;
    }

    // Clear previous content
    container.innerHTML = '';

    if (mediaItem.error) {
        console.error('[Google Photos] Media item error:', mediaItem.error);
        container.innerHTML = `<div class="error-message">${mediaItem.error}</div>`;
        return;
    }

    console.log('[Google Photos] Processing media item:', {
        filename: mediaItem.filename,
        mimeType: mediaItem.mimeType,
        baseUrl: mediaItem.baseUrl
    });

    // Create progress bar
    const progressBar = document.createElement('div');
    progressBar.id = 'photo-progress';
    progressBar.className = 'photo-progress';
    container.appendChild(progressBar);

    // Create media element
    let mediaElement;
    if (mediaItem.mimeType && mediaItem.mimeType.startsWith('video/')) {
        mediaElement = document.createElement('video');
        mediaElement.autoplay = true;
        mediaElement.loop = true;
        mediaElement.muted = true;
        mediaElement.controls = false;
        mediaElement.src = mediaItem.baseUrl + '=dv';
        console.log('[Google Photos] Video URL:', mediaElement.src);
    } else {
        mediaElement = document.createElement('img');
        // Add proper parameters for image URL
        const imageUrl = `${mediaItem.baseUrl}=w1920-h1080-c`;
        mediaElement.src = imageUrl;
        mediaElement.alt = mediaItem.filename || '';
        console.log('[Google Photos] Image URL:', imageUrl);
    }

    mediaElement.onerror = (error) => {
        console.error('[Google Photos] Error loading media:', error);
        container.innerHTML = `<div class="error-message">Error loading media: ${error.message}</div>`;
    };

    mediaElement.onload = () => {
        console.log('[Google Photos] Media loaded successfully:', mediaItem.filename);
        container.appendChild(mediaElement);
        startProgressBar();
    };

    // For video, append immediately (onload doesn't fire for video)
    if (mediaItem.mimeType && mediaItem.mimeType.startsWith('video/')) {
        container.appendChild(mediaElement);
        startProgressBar();
    }

    // Show album title
    const infoDiv = document.createElement('div');
    infoDiv.className = 'photo-info';
    infoDiv.textContent = currentAlbum;
    container.appendChild(infoDiv);
}

function nextMedia() {
    if (currentBatch.length === 0) {
        console.warn('[Google Photos] No current batch, fetching new batch...');
        updatePhotoBatch();
        return;
    }

    currentIndex = (currentIndex + 1) % currentBatch.length;
    console.log(`[Google Photos] Showing next media: index ${currentIndex} of ${currentBatch.length}`);
    showMedia(currentBatch[currentIndex]);
}

function updatePhotoBatch() {
    console.log('[Google Photos] Fetching new photo batch from API...');
    fetch('/api/plugins/google-photos/data')
        .then(response => {
            if (!response.ok) {
                console.error('[Google Photos] API response not OK:', response.status, response.statusText);
                throw new Error(`API response not OK: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[Google Photos] Received API response:', data);
            if (data.error) {
                console.error('[Google Photos] API error:', data.error);
                throw new Error(data.error);
            }
            if (!data.media || !Array.isArray(data.media)) {
                console.error('[Google Photos] Invalid media data:', data);
                throw new Error('Invalid media data received from API');
            }
            currentBatch = data.media;
            currentAlbum = currentBatch.length > 0 ? currentBatch[0].albumTitle : '';
            currentIndex = 0;
            console.log(`[Google Photos] Received batch with ${currentBatch.length} items. Album: ${currentAlbum}`);
            if (currentBatch.length > 0) {
                showMedia(currentBatch[0]);
            } else {
                console.warn('[Google Photos] Batch is empty!');
                const container = document.getElementById('photo-container');
                if (container) {
                    container.innerHTML = '<div class="error-message">No photos found in this album.</div>';
                }
            }
        })
        .catch(error => {
            console.error('[Google Photos] Error fetching new photo batch:', error);
            const container = document.getElementById('photo-container');
            if (container) {
                container.innerHTML = `<div class="error-message">Error fetching photos: ${error.message}</div>`;
            }
        });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Google Photos] DOMContentLoaded, initializing photo batch...');
    updatePhotoBatch();
}); 