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
    
    // Configuration (should match config.json)
    const config = {
        displayDuration: 15000, // 15 seconds
        transitionDuration: 2000, // 2 seconds
        updateInterval: 15000 // Check for new photos every 15 seconds
    };
    
    function showLoading() {
        loading.style.display = 'block';
        errorDiv.style.display = 'none';
        img.style.opacity = '0';
    }
    
    function hideLoading() {
        loading.style.display = 'none';
    }
    
    function showError(message, detail = '') {
        console.error('Nature Photos Error:', message, detail);
        errorDiv.style.display = 'block';
        loading.style.display = 'none';
        img.style.opacity = '0';
        
        const errorText = errorDiv.querySelector('.error-text');
        const errorDetail = errorDiv.querySelector('.error-detail');
        
        if (errorText) errorText.textContent = message;
        if (errorDetail) errorDetail.textContent = detail;
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
            // Fade out current image
            img.classList.add('fade-out');
            
            setTimeout(() => {
                // Set new image
                img.src = newImg.src;
                img.alt = photo.description || 'Nature photo';
                
                // Fade in new image
                img.classList.remove('fade-out');
                img.classList.add('loaded');
                
                hideLoading();
                errorDiv.style.display = 'none';
                
                console.log('Photo loaded successfully:', photo.id);
            }, config.transitionDuration / 2);
        };
        
        newImg.onerror = function() {
            console.error('Failed to load image:', photo.url);
            showError('Failed to load image', 'Image URL may be invalid or unavailable');
        };
        
        newImg.src = photo.url;
        currentPhoto = photo;
    }
    
    function fetchPhoto() {
        console.log('Fetching new photo...');
        showLoading();
        
        fetch('/api/plugins/random-nature-photos/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Photo data received:', data);
                displayPhoto(data);
            })
            .catch(error => {
                console.error('Error fetching photo:', error);
                showError('Failed to fetch photo from server', error.message);
            });
    }
    
    function startSlideshow() {
        console.log('Starting nature photos slideshow');
        
        // Initial load
        fetchPhoto();
        
        // Set interval for photo changes
        if (slideInterval) {
            clearInterval(slideInterval);
        }
        
        slideInterval = setInterval(() => {
            fetchPhoto();
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
    
    // Handle visibility changes (pause when hidden)
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            console.log('Page hidden - pausing slideshow');
            stopSlideshow();
        } else {
            console.log('Page visible - resuming slideshow');
            startSlideshow();
        }
    });
    
    // Handle window focus changes
    window.addEventListener('focus', function() {
        console.log('Window focused - ensuring slideshow is running');
        if (!slideInterval) {
            startSlideshow();
        }
    });
    
    window.addEventListener('blur', function() {
        console.log('Window blurred - pausing slideshow');
        stopSlideshow();
    });
    
    // Error recovery - restart slideshow if it stops
    function checkSlideshow() {
        if (!slideInterval && !document.hidden) {
            console.log('Slideshow appears to have stopped - restarting');
            startSlideshow();
        }
    }
    
    // Check slideshow health every minute
    setInterval(checkSlideshow, 60000);
    
    // Start the slideshow
    startSlideshow();
    
    // Make functions available for debugging
    window.naturePhotos = {
        fetchPhoto,
        startSlideshow,
        stopSlideshow,
        getCurrentPhoto: () => currentPhoto
    };
} 