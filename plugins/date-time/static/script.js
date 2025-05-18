/**
 * Date Time Plugin - Displays current time and date
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('plugin-date-time');
    if (!container) return;
    
    // Initialize
    dateTimeInit(container);
});

function dateTimeInit(container) {
    // Get plugin configuration
    const pluginObj = window.PLUGINS?.find(p => p.name === 'date-time');
    const pluginConfig = pluginObj?.config || {};
    const pluginData = window.PLUGINS_DATA?.['date-time'] || {};
    
    // DOM elements
    const timeElement = container.querySelector('#datetime-time');
    const dateElement = container.querySelector('#datetime-date');
    
    // Apply font sizes from config
    timeElement.style.cssText += `font-size: ${pluginConfig.format.time_font_size} !important;`;
    dateElement.style.cssText += `font-size: ${pluginConfig.format.date_font_size} !important;`;
    
    // Display initial data
    timeElement.textContent = pluginData.data?.time || '--:--';
    dateElement.textContent = pluginData.data?.date || '----.--.--';
    
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
                timeElement.classList.add('error');
                dateElement.classList.add('error');
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 10;
    setInterval(fetchDateTime, refreshInterval * 1000);
} 