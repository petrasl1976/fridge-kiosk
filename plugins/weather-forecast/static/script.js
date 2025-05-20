/**
 * Weather Forecast Plugin - Displays weather forecast for the next 7 days
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.weather-forecast');
    if (!container) return;
    
    // Initialize
    weatherForecastInit(container);
});

function weatherForecastInit(container) {
    // Get plugin configuration and data
    const plugin = window.PLUGINS?.['weather-forecast'] || {};
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
    
    // Function to fetch weather data from the API
    function fetchWeatherData() {
        fetch('/api/plugins/weather-forecast/data')
            .then(response => response.json())
            .then(data => {
                if (data) {
                    let html = '';
                    
                    // Add current weather section if available
                    if (data.current) {
                        const current = data.current;
                        const currentTime = new Date(current.dt * 1000);
                        const timeStr = currentTime.toTimeString().substring(0, 5);
                        const iconPath = `/plugins/weather-forecast/icons/${current.conditionCode}.png`;
                        
                        html += `
                            <div class="weather-current">
                                <div class="current-header">Now: ${timeStr}</div>
                                <div class="current-icon">
                                    <img src="${iconPath}" 
                                         alt="${current.conditionCode}"
                                         onerror="this.src='/plugins/weather-forecast/icons/clear.png'">
                                </div>
                                <div class="current-details">
                                    <div class="current-temp">Temp: ${Math.round(current.temperature)}°</div>
                                    <div class="current-feels">Feels like: ${Math.round(current.feelsLike)}°</div>
                                    <div class="current-wind">Wind: ${current.windSpeed} m/s</div>
                                    <div class="current-pressure">Pressure: ${current.pressure} hPa</div>
                                    <div class="current-humidity">Humidity: ${current.humidity}%</div>
                                    <div class="current-precipitation">Precipitation: ${current.precipitation} mm</div>
                                </div>
                            </div>
                            <div class="divider"></div>
                        `;
                    }
                    
                    // Add daily forecast
                    if (data.daily) {
                        html += data.daily.map(day => {
                            const date = new Date(day.dt * 1000);
                            const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
                            const condition = day.weather[0].description;
                            const iconPath = `/plugins/weather-forecast/icons/${condition}.png`;
                            
                            return `
                                <div class="weather-day">
                                    <div class="date">${dayName}</div>
                                    <div class="temp">
                                        <span class="max">${Math.round(day.main.temp_max)}°</span>
                                        <span class="min">${Math.round(day.main.temp_min)}°</span>
                                    </div>
                                    <div class="condition">
                                        <img src="${iconPath}" 
                                             alt="${condition}"
                                             onerror="this.src='/plugins/weather-forecast/icons/clear.png'">
                                    </div>
                                </div>
                            `;
                        }).join('');
                    }
                    
                    container.innerHTML = html;
                }
            })
            .catch(error => {
                console.error('Error fetching weather data:', error);
                container.innerHTML = '<div class="error">Error loading weather data</div>';
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 3600;
    fetchWeatherData(); // Get data immediately
    setInterval(fetchWeatherData, refreshInterval * 1000);
} 