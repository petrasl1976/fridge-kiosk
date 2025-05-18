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
    
    console.log('Date-time initial plugin data:', pluginData);
    
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
        console.log('Setting initial date-time from backend data:', pluginData.data);
        timeElement.textContent = pluginData.data.time;
        dateElement.textContent = pluginData.data.date;
    } else {
        console.log('No initial date-time data available from backend');
        displayErrorMessage("Can't get data from backend /date-time/data");
    }
    
    // Function to display error message
    function displayErrorMessage(message) {
        console.error('Date-time error:', message);
        
        // Simple error placeholders
        timeElement.textContent = "Error:";
        dateElement.textContent = message;
        
        // Add error styling
        timeElement.classList.add('error');
        dateElement.classList.add('error');
    }
    
    // Function to fetch date and time from the API
    function fetchDateTime() {
        console.log('Fetching real-time date and time...');
        fetch('/api/plugins/date-time/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Check if the response contains an error
                if (data.error) {
                    console.error('Backend returned an error:', data.error);
                    displayErrorMessage(data.error);
                    return;
                }
                
                // Update the display with valid data
                console.log('Received updated date-time:', data);
                timeElement.textContent = data.time;
                dateElement.textContent = data.date;
                
                // Remove any error styling if it was previously applied
                timeElement.classList.remove('error');
                dateElement.classList.remove('error');
            })
            .catch(error => {
                console.error('Error fetching date-time data:', error);
                displayErrorMessage("Can't get data from backend");
            });
    }
    
    // Set up automatic updates from backend only
    const refreshInterval = config.updateInterval || 10;
    console.log(`Setting up date-time refresh every ${refreshInterval} seconds`);
    
    // Set up API update at the specified interval
    setInterval(fetchDateTime, refreshInterval * 1000);
    
    // Initial fetch (if not already loaded from backend)
    if (!pluginData.data) {
        console.log('Performing initial date-time fetch');
        fetchDateTime();
    } else {
        console.log('Skipping initial fetch as data was provided by backend');
    }
    
    console.log('Date-time plugin initialized with interval:', refreshInterval);
} 