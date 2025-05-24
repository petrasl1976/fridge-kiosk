document.addEventListener('DOMContentLoaded', function() {
    let currentIndex = 0;
    let mediaItems = [];
    let currentTimeout = null;

    function updateDisplay() {
        const container = document.querySelector('.photo-container');
        const overlay = document.querySelector('.photo-overlay');
        const albumTitle = document.querySelector('.album-title');
        const photoFilename = document.querySelector('.photo-filename');

        if (!mediaItems.length) {
            container.innerHTML = '<div class="no-photos">No photos available</div>';
            return;
        }

        const item = mediaItems[currentIndex];
        const isVideo = item.mimeType.startsWith('video/');
        
        // Clear previous media
        container.innerHTML = '';
        
        if (isVideo) {
            const video = document.createElement('video');
            video.src = item.baseUrl;
            video.autoplay = true;
            video.muted = !item.settings?.VIDEO_SOUND;
            video.controls = false;
            video.loop = true;
            container.appendChild(video);
            
            // Set timeout for video duration
            if (currentTimeout) clearTimeout(currentTimeout);
            currentTimeout = setTimeout(() => {
                currentIndex = (currentIndex + 1) % mediaItems.length;
                updateDisplay();
            }, (item.settings?.VIDEO_DURATION || 30) * 1000);
        } else {
            const img = document.createElement('img');
            img.src = item.baseUrl;
            container.appendChild(img);
            
            // Set timeout for photo duration
            if (currentTimeout) clearTimeout(currentTimeout);
            currentTimeout = setTimeout(() => {
                currentIndex = (currentIndex + 1) % mediaItems.length;
                updateDisplay();
            }, (item.settings?.PHOTO_DURATION || 10) * 1000);
        }

        // Update overlay info
        if (item.settings?.PHOTO_INFO_OVERLAY) {
            albumTitle.textContent = item.albumTitle || 'Unknown Album';
            photoFilename.textContent = item.filename || 'Unknown File';
            overlay.style.display = 'block';
        } else {
            overlay.style.display = 'none';
        }
    }

    function loadNewPhotos() {
        fetch('/api/plugins/google-photos/data')
            .then(response => response.json())
            .then(data => {
                if (data.mediaItems && data.mediaItems.length > 0) {
                    mediaItems = data.mediaItems;
                    currentIndex = 0;
                    updateDisplay();
                }
            })
            .catch(error => {
                console.error('Error loading photos:', error);
            });
    }

    // Initial load
    loadNewPhotos();

    // Refresh photos every 5 minutes
    setInterval(loadNewPhotos, 5 * 60 * 1000);
}); 