/**
 * Date Time Plugin - Displays current time and date
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('date-time');
    if (!container) return;
    
    // Initialize
    dateTimeInit(container);
});

function dateTimeInit(container) {
    // Get plugin configuration
    const plugin = window.PLUGINS?.['date-time'] || {};
    const pluginConfig = plugin.config || {};
    
    // DOM elements
    const timeElement = container.querySelector('#date-time-time');
    const dateElement = container.querySelector('#date-time-date');
    
    // Function to fetch date and time from the API
    function fetchDateTime() {
        fetch('/api/plugins/date-time/data')
            .then(response => response.json())
            .then(data => {
                if (data.time) timeElement.textContent = data.time;
                if (data.date) dateElement.textContent = data.date;
            })
            .catch(() => {
                timeElement.textContent = 'Error';
                dateElement.textContent = 'Connection failed';
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 10;
    fetchDateTime(); // Fetch data immediately
    setInterval(fetchDateTime, refreshInterval * 1000);
} 