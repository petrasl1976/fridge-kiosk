/**
 * Google Calendar Plugin - Displays calendar events in a monthly grid view
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.calendar-widget');
    if (!container) return;
    
    // Initialize
    calendarInit(container);

    // Initialize weather containers
    const weatherContainers = document.querySelectorAll('.weather-forecast-container');
    
    // Function to update weather data
    async function updateWeatherData() {
        try {
            // Get weather data from the weather plugin
            const response = await fetch('/api/plugins/weather-forecast/data');
            const weatherData = await response.json();
            
            if (!weatherData || !weatherData.daily) {
                console.error('Invalid weather data received');
                return;
            }
            
            // Update each weather container
            weatherContainers.forEach(container => {
                const timestamp = parseInt(container.dataset.timestamp);
                const dayData = weatherData.daily.find(day => {
                    const dayDate = new Date(day.dt * 1000);
                    const containerDate = new Date(timestamp * 1000);
                    return dayDate.toDateString() === containerDate.toDateString();
                });
                
                if (dayData) {
                    const tempMin = Math.round(dayData.main.temp_min);
                    const tempMax = Math.round(dayData.main.temp_max);
                    const condition = dayData.weather[0].description;
                    
                    // Create weather display: min (blue, large), max (red, large), icon below
                    container.innerHTML = `
                        <div style="display: flex; align-items: baseline; gap: 6px; margin-top: 2px;">
                            <span style="color: #2196f3; font-size: 1.3em; font-weight: bold;">${tempMin}°</span>
                            <span style="color: #e53935; font-size: 1.3em; font-weight: bold;">${tempMax}°</span>
                        </div>
                        <div style="margin-top: 2px;">
                            <img src="/plugins/weather-forecast/icons/${condition}.png" 
                                 alt="${condition}" 
                                 style="width: 28px; height: 28px; display: block;">
                        </div>
                    `;
                }
            });
        } catch (error) {
            console.error('Error updating weather data:', error);
        }
    }
    
    // Initial weather update
    updateWeatherData();
    
    // Update weather data every 5 minutes
    setInterval(updateWeatherData, 5 * 60 * 1000);
});

function calendarInit(container) {
    // Get plugin configuration and data
    const plugin = window.PLUGINS?.['google-calendar'] || {};
    const pluginConfig = plugin.config || {};
    const pluginData = plugin.data || {};
    
    // Apply font size and other styles from config
    if (container) {
        container.style.cssText += `
            font-size: ${pluginConfig.format.font_size} !important;
            color: ${pluginConfig.format.color} !important;
            padding: ${pluginConfig.format.padding} !important;
        `;
    }
    
    // Function to fetch calendar data from the API
    function fetchCalendarData() {
        fetch('/api/plugins/google-calendar/data')
            .then(response => response.json())
            .then(data => {
                if (data && data.weeks) {
                    // The plugin will handle rendering with the updated data
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error fetching calendar data:', error);
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 900;
    setInterval(fetchCalendarData, refreshInterval * 1000);
}

// Helper function to convert event summary to a color
function getEventColor(summary) {
    if (!summary) return "#000000"; // Black for empty summaries
    
    // Get the event colors from the kiosk config
    const userColors = window.KIOSK_CONFIG?.userColors || {};
    console.debug("Available userColors:", userColors);
    
    // Use the first 2 characters as the key (similar to how discord username colors work)
    const key = summary.substring(0, 2).toUpperCase(); 
    console.debug(`Getting color for key: ${key}`);
    
    // Use the color from userColors if it exists, otherwise use black
    const color = userColors[key] || "#000000"; // Black default
    console.debug(`Using color: ${color} for summary: ${summary}`);
    return color;
} 