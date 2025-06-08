// Random Nature Photos Plugin JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.nature-photos-container');
    if (container) {
        naturePhotosInit(container);
    }
});

function naturePhotosInit(container) {
    console.log('Initializing Random Nature Photos plugin');
    
    const img = container.querySelector('#nature-photo-img');
    const loading = container.querySelector('#nature-loading');
    const errorDiv = container.querySelector('#nature-error');
    const photoDescription = container.querySelector('#photo-description');
    const photoCredits = container.querySelector('#photo-credits');
    const photoCounter = container.querySelector('#photo-counter');
    
    let currentPhoto = null;
    let slideInterval = null;
    let isLoading = false;
    let lastPhotoTime = 0;
    let isInitialized = false;
    
    // Configuration (should match config.json)
    const config = {
        displayDuration: 15000, // 15 seconds
        transitionDuration: 2000, // 2 seconds
        minDisplayTime: 5000 // Minimum time to show a photo before allowing next
    };
    
    function showLoading() {
        if (isLoading) return; // Prevent multiple loading states
        isLoading = true;
        loading.style.display = 'block';
        errorDiv.style.display = 'none';
        console.log('Showing loading indicator');
    }
    
    function hideLoading() {
        isLoading = false;
        loading.style.display = 'none';
        console.log('Hiding loading indicator');
    }
    
    function showError(message, detail = '') {
        console.error('Nature Photos Error:', message, detail);
        isLoading = false;
        errorDiv.style.display = 'block';
        loading.style.display = 'none';
        
        const errorText = errorDiv.querySelector('.error-text');
        const errorDetail = errorDiv.querySelector('.error-detail');
        
        if (errorText) errorText.textContent = message;
        if (errorDetail) errorDetail.textContent = detail;
        
        // Try again after 30 seconds if error
        setTimeout(() => {
            if (errorDiv.style.display !== 'none') {
                console.log('Retrying after error...');
                fetchPhoto();
            }
        }, 30000);
    }
    
    function updatePhotoInfo(photo) {
        if (photoDescription) {
            photoDescription.textContent = photo.description || 'Beautiful nature photography';
        }
        
        if (photoCredits) {
            photoCredits.textContent = `Photo by ${photo.photographer}`;
        }
    }
    
    function updateCounter(current, total) {
        if (photoCounter) {
            photoCounter.textContent = `${current} / ${total}`;
        }
    }
    
    function displayPhoto(photoData) {
        if (photoData.error) {
            showError(photoData.message || 'Failed to load photo', photoData.error);
            return;
        }
        
        const photo = photoData.photo;
        if (!photo || !photo.url) {
            showError('No photo data available');
            return;
        }
        
        console.log('Loading photo:', photo.id, photo.description);
        
        // Update info immediately
        updatePhotoInfo(photo);
        updateCounter(photoData.current_index, photoData.total_photos);
        
        // Pre-load the image
        const newImg = new Image();
        
        newImg.onload = function() {
            console.log('Photo loaded successfully, displaying immediately');
            
            // Set new image immediately - no transitions
            img.src = newImg.src;
            img.alt = photo.description || 'Nature photo';
            img.style.opacity = '1';
            
            hideLoading();
            errorDiv.style.display = 'none';
            
            // Record when photo was displayed
            lastPhotoTime = Date.now();
            currentPhoto = photo;
            
            console.log('Photo displayed successfully:', photo.id);
            console.log(`Next photo in ${config.displayDuration/1000} seconds`);
        };
        
        newImg.onerror = function() {
            console.error('Failed to load image:', photo.url);
            showError('Failed to load image', 'Image URL may be invalid or unavailable');
        };
        
        newImg.src = photo.url;
    }
    
    function fetchPhoto(isInitial = false) {
        // Prevent fetching too frequently
        const timeSinceLastPhoto = Date.now() - lastPhotoTime;
        if (timeSinceLastPhoto < config.minDisplayTime && currentPhoto && !isInitial) {
            console.log(`Skipping fetch - too soon since last photo (${timeSinceLastPhoto}ms < ${config.minDisplayTime}ms)`);
            return;
        }
        
        if (isLoading) {
            console.log('Already loading, skipping fetch');
            return;
        }
        
        // Use /data for initial photo, /next for slideshow
        const endpoint = isInitial ? '/api/plugins/random-nature-photos/data' : '/api/plugins/random-nature-photos/next';
        console.log(`Fetching ${isInitial ? 'initial' : 'next'} photo from ${endpoint}...`);
        showLoading();
        
        fetch(endpoint, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache'
            }
        })
            .then(response => {
                console.log('Response received:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Photo data received:', data);
                if (data.error) {
                    showError(data.message || 'API returned error', data.error);
                } else {
                    displayPhoto(data);
                }
            })
            .catch(error => {
                console.error('Error fetching photo:', error);
                showError('Failed to fetch photo from server', error.message);
            });
    }
    
    function startSlideshow() {
        if (slideInterval) {
            console.log('Slideshow already running, stopping old one first');
            stopSlideshow();
        }
        
        console.log('Starting nature photos slideshow');
        
        // Load first photo immediately if we don't have one
        if (!currentPhoto) {
            fetchPhoto(true); // Initial photo
        }
        
        // Set interval for subsequent photos
        slideInterval = setInterval(() => {
            console.log('Slideshow interval triggered - requesting next photo');
            fetchPhoto(false); // Next photo
        }, config.displayDuration);
        
        console.log(`Slideshow started - photos will change every ${config.displayDuration/1000} seconds`);
    }
    
    function stopSlideshow() {
        if (slideInterval) {
            clearInterval(slideInterval);
            slideInterval = null;
            console.log('Slideshow stopped');
        }
    }
    
    // Only set up event listeners once
    if (!isInitialized) {
        console.log('Setting up event listeners');
        
        // Handle visibility changes (pause when hidden)
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                console.log('Page hidden - pausing slideshow');
                stopSlideshow();
            } else {
                console.log('Page visible - resuming slideshow');
                setTimeout(() => {
                    if (!slideInterval) {
                        startSlideshow();
                    }
                }, 1000);
            }
        });
        
        // Handle window focus changes
        window.addEventListener('focus', function() {
            console.log('Window focused');
            setTimeout(() => {
                if (!slideInterval && !document.hidden) {
                    startSlideshow();
                }
            }, 1000);
        });
        
        window.addEventListener('blur', function() {
            console.log('Window blurred');
            // Don't stop slideshow on blur, only on visibility change
        });
        
        isInitialized = true;
    }
    
    // Start the slideshow after a small delay
    setTimeout(() => {
        if (!slideInterval) {
            startSlideshow();
        }
    }, 2000);
    
    // Make functions available for debugging
    window.naturePhotos = {
        fetchPhoto,
        startSlideshow,
        stopSlideshow,
        getCurrentPhoto: () => currentPhoto,
        getConfig: () => config,
        isLoading: () => isLoading,
        timeSinceLastPhoto: () => Date.now() - lastPhotoTime,
        hasInterval: () => !!slideInterval
    };
} 