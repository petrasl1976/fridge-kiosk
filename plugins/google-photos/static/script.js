let currentBatch = [];
let currentIndex = 0;
let currentAlbum = "";
let progressIntervalId = null;
let retryCount = 0;
const MAX_RETRIES = 3;

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
    // Always define fontSize at the start
    let fontSize = '1.3em';
    try {
        fontSize = window.PLUGINS?.['google-photos']?.config?.settings?.label_font_size || fontSize;
    } catch (e) { /* fallback to default */ }

    console.log('[Google Photos] Starting showMedia function');
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

    // --- Add album and file name info above the photo ---
    // Album name (top line)
    const albumDiv = document.createElement('div');
    albumDiv.className = 'photo-album';
    albumDiv.textContent = mediaItem.album && mediaItem.album.title ? mediaItem.album.title : '';
    albumDiv.style.fontSize = fontSize;
    container.appendChild(albumDiv);

    // File time (second line, when it was taken)
    const fileDiv = document.createElement('div');
    fileDiv.className = 'photo-filename';
    let takenTime = '';
    if (mediaItem.mediaMetadata && mediaItem.mediaMetadata.creationTime) {
        // Format as YYYY-MM-DD HH:mm
        const date = new Date(mediaItem.mediaMetadata.creationTime);
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        const hh = String(date.getHours()).padStart(2, '0');
        const min = String(date.getMinutes()).padStart(2, '0');
        takenTime = `${yyyy}-${mm}-${dd} ${hh}:${min}`;
    }
    fileDiv.textContent = takenTime;
    fileDiv.style.fontSize = fontSize;
    container.appendChild(fileDiv);
    // --- End info lines ---

    console.log('[Google Photos] Processing media item:', {
        filename: mediaItem.filename,
        mimeType: mediaItem.mimeType,
        baseUrl: mediaItem.baseUrl,
        albumTitle: mediaItem.albumTitle
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
        
        // Add loading state
        mediaElement.style.opacity = '0';
        mediaElement.style.transition = 'opacity 0.5s ease-in-out';
    }

    // Add loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    loadingDiv.textContent = 'Loading...';
    container.appendChild(loadingDiv);

    mediaElement.onerror = (error) => {
        console.error('[Google Photos] Error loading media:', error);
        loadingDiv.remove();
        if (retryCount < MAX_RETRIES) {
            retryCount++;
            console.log(`[Google Photos] Retrying media load (attempt ${retryCount}/${MAX_RETRIES})...`);
            setTimeout(() => showMedia(mediaItem), 1000);
        } else {
            retryCount = 0;
            container.innerHTML = `<div class="error-message">Error loading media: ${error.message}</div>`;
            setTimeout(nextMedia, 5000); // Try next media after 5 seconds
        }
    };

    mediaElement.onload = () => {
        console.log('[Google Photos] Media loaded successfully:', mediaItem.filename);
        retryCount = 0; // Reset retry count on successful load
        loadingDiv.remove();
        mediaElement.style.opacity = '1';
        mediaElement.classList.add('loaded');
        container.appendChild(mediaElement);

        // Portrait/landscape logic for images
        if (mediaElement.tagName === 'IMG') {
            if (mediaElement.naturalHeight > mediaElement.naturalWidth) {
                // Portrait: full height
                mediaElement.style.height = '100%';
                mediaElement.style.width = 'auto';
            } else {
                // Landscape: full width
                mediaElement.style.width = '100%';
                mediaElement.style.height = 'auto';
            }
        }

        startProgressBar();
    };

    // For video, append immediately (onload doesn't fire for video)
    if (mediaItem.mimeType && mediaItem.mimeType.startsWith('video/')) {
        loadingDiv.remove();
        container.appendChild(mediaElement);
        mediaElement.classList.add('loaded');
        startProgressBar();
    }
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
                // Retry after 5 seconds
                setTimeout(updatePhotoBatch, 5000);
            }
        });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Google Photos] DOMContentLoaded, initializing photo batch...');
    // Add container check
    const container = document.getElementById('photo-container');
    if (!container) {
        console.error('[Google Photos] photo-container not found in DOM');
        return;
    }
    console.log('[Google Photos] Container found, dimensions:', {
        width: container.offsetWidth,
        height: container.offsetHeight
    });
    updatePhotoBatch();
}); 