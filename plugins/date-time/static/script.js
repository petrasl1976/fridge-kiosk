/**
 * Date Time Plugin for Fridge Kiosk
 * Displays current time and date
 */

// Initialize the date-time plugin when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get plugin container
    const container = document.getElementById('plugin-date-time');
    if (!container) {
        console.error('Date-time plugin: Container not found');
        return;
    }
    
    // Initialize
    dateTimeInit(container);
});

// Initialize the date-time plugin
function dateTimeInit(container) {
    console.log('Initializing Date-time plugin');
    
    // Get config from global object
    const config = window.KIOSK_CONFIG?.plugins?.['date-time'] || {};
    const pluginData = window.PLUGINS_DATA?.['date-time'] || {};
    
    // DOM elements
    const timeElement = container.querySelector('#datetime-time');
    const dateElement = container.querySelector('#datetime-date');
    
    // Apply font sizes from config
    if (config.format) {
        if (config.format.time_font_size) {
            timeElement.style.fontSize = config.format.time_font_size;
        }
        if (config.format.date_font_size) {
            dateElement.style.fontSize = config.format.date_font_size;
        }
    }
    
    // Display initial data if available from the backend
    if (pluginData.data) {
        timeElement.textContent = pluginData.data.time;
        dateElement.textContent = pluginData.data.date;
    }
    
    // Function to fetch date and time from the API
    function fetchDateTime() {
        fetch('/api/plugins/date-time/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Update the display
                timeElement.textContent = data.time;
                dateElement.textContent = data.date;
            })
            .catch(error => {
                console.error('Error fetching date-time data:', error);
            });
    }
    
    // Set up automatic updates
    const refreshInterval = config.updateInterval || 60;
    setInterval(fetchDateTime, refreshInterval * 1000);
    
    // Initial fetch (if not already loaded from backend)
    if (!pluginData.data) {
        fetchDateTime();
    }
    
    console.log('Date-time plugin initialized with interval:', refreshInterval);
} 