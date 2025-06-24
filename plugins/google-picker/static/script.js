let currentBatch = [];
let currentIndex = 0;
let progressIntervalId = null;
let retryCount = 0;
const MAX_RETRIES = 3;

function startProgressBar(mediaItem) {
    if (progressIntervalId) {
        clearInterval(progressIntervalId);
    }

    // Get durations from config
    let photoDuration = 30;
    let videoDuration = 60;
    try {
        const settings = window.PLUGINS?.['google-picker']?.config?.settings || {};
        photoDuration = parseInt(settings.photo_duration) || photoDuration;
        videoDuration = parseInt(settings.video_duration) || videoDuration;
    } catch (e) { /* fallback to defaults */ }

    // Determine duration based on media type
    let duration = photoDuration;
    if (mediaItem && mediaItem.mimeType && mediaItem.mimeType.startsWith('video/')) {
        duration = videoDuration;
    }

    let timePassed = 0;
    const progressEl = document.getElementById('picker-photo-progress');
    if (progressEl) {
        progressEl.style.width = '100%';
    }

    progressIntervalId = setInterval(() => {
        timePassed++;
        const percentLeft = 100 - (timePassed / duration) * 100;
        if (progressEl) {
            progressEl.style.width = percentLeft + '%';
        }

        if (timePassed >= duration) {
            clearInterval(progressIntervalId);
            nextMedia();
        }
    }, 1000);
}

function showMedia(mediaItem) {
    console.log('[Google Picker] Starting showMedia function');
    const container = document.getElementById('picker-photo-container');
    if (!container) {
        console.error('[Google Picker] picker-photo-container not found in DOM');
        return;
    }

    // Clear previous content
    container.innerHTML = '';

    if (mediaItem.error) {
        console.error('[Google Picker] Media item error:', mediaItem.error);
        container.innerHTML = `<div class="error-message">${mediaItem.error}</div>`;
        return;
    }

    console.log('[Google Picker] Processing media item:', {
        mimeType: mediaItem.mimeType,
        mediaMetadata: mediaItem.mediaMetadata,
        baseUrl: mediaItem.baseUrl ? 'data URL present' : 'no baseUrl'
    });

    // Create progress bar
    const progressBar = document.createElement('div');
    progressBar.id = 'picker-photo-progress';
    progressBar.className = 'picker-photo-progress';
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
        console.log('[Google Picker] Video URL:', mediaElement.src);
    } else {
        mediaElement = document.createElement('img');
        // Use the baseUrl directly (it's now a data URL with embedded image data)
        mediaElement.src = mediaItem.baseUrl;
        mediaElement.alt = '';
        console.log('[Google Picker] Image URL type:', mediaItem.baseUrl.substring(0, 20) + '...');
        
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
        console.error('[Google Picker] Error loading media:', error);
        loadingDiv.remove();
        if (retryCount < MAX_RETRIES) {
            retryCount++;
            console.log(`[Google Picker] Retrying media load (attempt ${retryCount}/${MAX_RETRIES})...`);
            setTimeout(() => showMedia(mediaItem), 1000);
        } else {
            retryCount = 0;
            container.innerHTML = `<div class="error-message">Error loading media: ${error.message}</div>`;
            setTimeout(nextMedia, 5000); // Try next media after 5 seconds
        }
    };

    mediaElement.onload = () => {
        console.log('[Google Picker] Media loaded successfully:', mediaItem.filename);
        retryCount = 0; // Reset retry count on successful load
        loadingDiv.remove();
        mediaElement.style.opacity = '1';
        mediaElement.classList.add('loaded');
        container.appendChild(mediaElement);

        // Always align images to the bottom and center horizontally, regardless of orientation
        if (mediaElement.tagName === 'IMG') {
            mediaElement.style.position = 'absolute';
            mediaElement.style.left = '50%';
            mediaElement.style.bottom = '0';
            mediaElement.style.top = 'auto';
            mediaElement.style.transform = 'translateX(-50%)';
        }

        startProgressBar(mediaItem);
    };

    // For video, append immediately (onload doesn't fire for video)
    if (mediaItem.mimeType && mediaItem.mimeType.startsWith('video/')) {
        loadingDiv.remove();
        container.appendChild(mediaElement);
        mediaElement.classList.add('loaded');
        startProgressBar(mediaItem);
    }
}

function nextMedia() {
    if (currentBatch.length === 0) {
        console.warn('[Google Picker] No current batch, fetching new batch...');
        updatePhotoBatch();
        return;
    }

    if (currentIndex + 1 >= currentBatch.length) {
        // End of sequence: get a new batch with a new random starting point
        console.log('[Google Picker] End of sequence, fetching new batch...');
        updatePhotoBatch();
        return;
    }

    currentIndex = currentIndex + 1;
    console.log(`[Google Picker] Showing next media: index ${currentIndex} of ${currentBatch.length}`);
    showMedia(currentBatch[currentIndex]);
}

function updatePhotoBatch() {
    console.log('[Google Picker] Fetching photo batch from API...');
    fetch('/api/plugins/google-picker/data')
        .then(response => {
            if (!response.ok) {
                console.error('[Google Picker] API response not OK:', response.status, response.statusText);
                throw new Error(`API response not OK: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[Google Picker] Received API response:', data);
            if (data.error) {
                console.error('[Google Picker] API error:', data.error);
                throw new Error(data.error);
            }
            if (!data.media || !Array.isArray(data.media)) {
                console.error('[Google Picker] Invalid media data:', data);
                throw new Error('Invalid media data received from API');
            }
            
            if (data.media.length === 0) {
                // No photos available - show setup message
                const container = document.getElementById('picker-photo-container');
                if (container) {
                    container.innerHTML = `
                        <div class="setup-message">
                            <h3>📸 Google Photos Picker Setup Required</h3>
                            <p>No photos have been selected yet!</p>
                            <p>Run the setup utility to select photos from your Google Photos library:</p>
                            <code>python plugins/google-picker/picker_setup.py</code>
                            <p style="margin-top: 20px; font-size: 0.9em; opacity: 0.8;">
                                This is a one-time setup. You can select hundreds of photos at once.
                            </p>
                        </div>
                    `;
                }
                return;
            }
            
            currentBatch = data.media;
            currentIndex = 0;
            console.log(`[Google Picker] Received batch with ${currentBatch.length} items`);
            showMedia(currentBatch[0]);
        })
        .catch(error => {
            console.error('[Google Picker] Error fetching photo batch:', error);
            const container = document.getElementById('picker-photo-container');
            if (container) {
                container.innerHTML = `<div class="error-message">Error fetching photos: ${error.message}</div>`;
                // Retry after 10 seconds
                setTimeout(updatePhotoBatch, 10000);
            }
        });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Google Picker] DOMContentLoaded, initializing photo batch...');
    // Add container check
    const container = document.getElementById('picker-photo-container');
    if (!container) {
        console.error('[Google Picker] picker-photo-container not found in DOM');
        return;
    }
    console.log('[Google Picker] Container found, dimensions:', {
        width: container.offsetWidth,
        height: container.offsetHeight
    });
    updatePhotoBatch();
});

// ------------------------------------------------------------
// NEW: Simple Manage Albums overlay
// ------------------------------------------------------------

function createManageUI() {
    // Floating settings button
    const btn = document.createElement('button');
    btn.id = 'picker-manage-btn';
    btn.textContent = '⚙️';
    Object.assign(btn.style, {
        position: 'fixed',
        right: '10px',
        bottom: '10px',
        zIndex: 9999,
        fontSize: '1.5em',
        background: '#ffffffaa',
        border: '1px solid #888',
        borderRadius: '4px',
        cursor: 'pointer'
    });
    btn.addEventListener('click', openManageModal);
    document.body.appendChild(btn);

    // Modal container (hidden by default)
    const modal = document.createElement('div');
    modal.id = 'picker-manage-modal';
    Object.assign(modal.style, {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(0,0,0,0.7)',
        display: 'none',
        zIndex: 9998,
        color: '#fff',
        overflow: 'auto',
        padding: '40px'
    });
    modal.innerHTML = `
        <div id="picker-manage-content" style="max-width:600px;margin:0 auto;background:#222;padding:20px;border-radius:8px;">
            <h2>Google Photos Albums</h2>
            <div id="picker-album-list">Loading...</div>
            <hr/>
            <h3>Create new album</h3>
            <input id="picker-new-album-title" type="text" placeholder="Album title" style="width:80%;padding:6px;" />
            <button id="picker-create-album-btn" style="padding:6px 12px;margin-left:6px;">Create</button>
            <button id="picker-manage-close" style="float:right;padding:6px 12px;">Close</button>
        </div>`;
    document.body.appendChild(modal);

    // Close button handler
    modal.querySelector('#picker-manage-close').addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Create album handler
    modal.querySelector('#picker-create-album-btn').addEventListener('click', () => {
        const title = modal.querySelector('#picker-new-album-title').value.trim();
        if (!title) return alert('Enter album title');
        fetch(`/api/plugins/google-picker/create_album?title=${encodeURIComponent(title)}`)
            .then(r => r.json())
            .then(data => {
                if (data.error) return alert('Error: ' + data.error);
                alert('Album created');
                loadAlbumList();
            });
    });
}

function openManageModal() {
    const modal = document.getElementById('picker-manage-modal');
    if (!modal) return;
    modal.style.display = 'block';
    loadAlbumList();
}

function loadAlbumList() {
    const listDiv = document.getElementById('picker-album-list');
    listDiv.innerHTML = 'Loading...';
    fetch('/api/plugins/google-picker/albums')
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                listDiv.innerHTML = `<div style="color:red;">Error: ${data.error}</div>`;
                return;
            }
            if (!data.albums || data.albums.length === 0) {
                listDiv.innerHTML = '<p>No albums yet.</p>';
                return;
            }
            listDiv.innerHTML = '';
            data.albums.forEach(alb => {
                const row = document.createElement('div');
                row.style.marginBottom = '8px';
                row.innerHTML = `<strong>${alb.title}</strong> (${alb.mediaItemsCount || 0}) `;
                const btn = document.createElement('button');
                btn.textContent = 'Add photos';
                btn.style.marginLeft = '8px';
                btn.addEventListener('click', () => startImportFlow(alb.id));
                row.appendChild(btn);
                listDiv.appendChild(row);
            });
        });
}

function startImportFlow(albumId) {
    fetch(`/api/plugins/google-picker/start_import?albumId=${encodeURIComponent(albumId)}`)
        .then(r => r.json())
        .then(data => {
            if (data.error) return alert('Error: ' + data.error);
            const pickerUri = data.pickerUri;
            const sessionId = data.sessionId;
            window.open(pickerUri, '_blank');
            pollImportStatus(sessionId, albumId);
        });
}

function pollImportStatus(sessionId, albumId) {
    const interval = setInterval(() => {
        fetch(`/api/plugins/google-picker/poll_import?sessionId=${encodeURIComponent(sessionId)}`)
            .then(r => r.json())
            .then(data => {
                if (data.status === 'waiting') {
                    console.log('Import waiting...');
                    return;
                }
                clearInterval(interval);
                if (data.error) {
                    alert('Import error: ' + data.error);
                } else {
                    alert(`Added ${data.added} items to album.`);
                    loadAlbumList();
                }
            });
    }, 5000);
}

// Initialize manage UI once DOM ready
document.addEventListener('DOMContentLoaded', createManageUI); 