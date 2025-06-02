/**
 * Google Calendar Plugin - Displays calendar events in a monthly grid view
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.calendar-widget');
    if (!container) return;
    
    // Initialize
    calendarInit(container);
});

function calendarInit(container) {
    // Get plugin configuration and data
    const plugin = window.PLUGINS?.['google-calendar-summary'] || {};
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
        fetch('/api/plugins/google-calendar-summary/data')
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