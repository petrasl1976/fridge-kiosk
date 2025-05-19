/**
 * Fridge Kiosk - Main JavaScript
 * Handles system-wide functionality and plugin initialization
 */

// When DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get configuration from window object (set by the backend)
    const config = window.KIOSK_CONFIG || {};
    
    // Set up system
    setupSystem(config);
    
    // Initialize the kiosk
    initKiosk();
});

/**
 * Set up system-wide settings and event listeners
 */
function setupSystem(config) {
    // Set theme based on config
    const theme = config.system?.theme || 'dark';
    document.body.classList.add(`theme-${theme}`);
    
    // Set orientation based on screen size
    updateOrientation();
    
    // Add event listeners
    window.addEventListener('resize', function() {
        updateOrientation();
    });
    
    // Set up periodic status check
    setInterval(checkSystemStatus, 30000); // Every 30 seconds
}

/**
 * Update orientation based on screen size
 */
function updateOrientation() {
    const isLandscape = window.innerWidth > window.innerHeight;
    document.body.classList.remove('orientation-landscape', 'orientation-portrait');
    document.body.classList.add(`orientation-${isLandscape ? 'landscape' : 'portrait'}`);
}

/**
 * Initialize the kiosk
 */
function initKiosk() {
    // Any additional initialization can go here
}

/**
 * Perform periodic system status check
 */
function checkSystemStatus() {
    // Check the status of plugins and system
    
    // You could ping the backend for status updates if needed
    // fetch('/api/system/status').then(response => response.json()).then(data => {...});
} 