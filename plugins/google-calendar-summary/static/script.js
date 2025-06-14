/**
 * Google Calendar Summary Plugin - Displays summary of events with weather
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.calendar-summary-widget');
    if (!container) return;
    
    // Initialize
    calendarSummaryInit(container);
});

function calendarSummaryInit(container) {
    // Get plugin configuration and data
    const plugin = window.PLUGINS?.['google-calendar-summary'] || {};
    const pluginConfig = plugin.config || {};
    const pluginData = plugin.data || {};
    
    // Apply font size and other styles from config
    if (container) {
        container.style.cssText += `
            font-size: ${pluginConfig.format?.font_size || '1.5em'} !important;
            color: ${pluginConfig.format?.color || '#fff'} !important;
            padding: ${pluginConfig.format?.padding || '10px'} !important;
        `;
    }
    
    // Function to fetch calendar and weather data from the API
    function fetchSummaryData() {
        fetch('/api/plugins/google-calendar-summary/data')
            .then(response => response.json())
            .then(data => {
                if (data && (data.today_events || data.tomorrow_events || data.weather_now)) {
                    // The plugin will handle rendering with the updated data
                    // We could update specific elements here, but for now reload to get fresh template
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error fetching calendar summary data:', error);
            });
    }
    
    // Function to specifically fetch weather data for dynamic updates
    function updateWeatherDisplay() {
        fetch('/api/plugins/weather-forecast/current')
            .then(response => response.json())
            .then(weatherData => {
                const weatherContainer = container.querySelector('.summary-weather-detailed');
                if (weatherContainer && weatherData && weatherData.temperature !== undefined) {
                    // Update temperature
                    const tempElement = weatherContainer.querySelector('.weather-temp');
                    if (tempElement) {
                        tempElement.textContent = `${weatherData.temperature}°C`;
                    }
                    
                    // Update condition
                    const conditionElements = weatherContainer.querySelectorAll('.weather-condition div');
                    if (conditionElements.length > 0) {
                        conditionElements[0].textContent = weatherData.conditionCode || '';
                    }
                    
                    // Update details
                    const detailsContainer = weatherContainer.querySelector('.weather-details');
                    if (detailsContainer) {
                        const detailDivs = detailsContainer.querySelectorAll('div');
                        if (detailDivs.length >= 4) {
                            detailDivs[0].textContent = `Jaučiasi: ${weatherData.feelsLike}°C`;
                            detailDivs[1].textContent = `Vėjas: ${weatherData.windSpeed} m/s`;
                            detailDivs[2].textContent = `Spaudimas: ${weatherData.pressure} hPa`;
                            detailDivs[3].textContent = `Drėgmė: ${weatherData.humidity}%`;
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error updating weather display:', error);
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 900;
    setInterval(fetchSummaryData, refreshInterval * 1000);
    
    // Update weather more frequently (every 5 minutes)
    setInterval(updateWeatherDisplay, 5 * 60 * 1000);
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