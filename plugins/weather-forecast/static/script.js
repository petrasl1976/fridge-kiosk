/**
 * Weather Forecast Plugin - Displays current weather and forecast
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('weather');
    if (!container) return;
    
    // Initialize
    weatherInit(container);
});

function weatherInit(container) {
    // Get plugin configuration
    const plugin = window.PLUGINS?.['weather-forecast'] || {};
    const pluginConfig = plugin.config || {};
    
    // DOM elements
    const timeElement = container.querySelector('#weather-time');
    const tempElement = container.querySelector('#weather-temp');
    const windElement = container.querySelector('#weather-wind');
    const pressureElement = container.querySelector('#weather-pressure');
    const conditionElement = container.querySelector('#weather-condition');
    const forecastContainer = container.querySelector('#weather-forecast');
    
    // Function to update forecast
    function updateForecast(daily) {
        const days = forecastContainer.querySelectorAll('.weather-day');
        daily.forEach((day, index) => {
            if (index >= days.length) return;
            
            const dayElement = days[index];
            const date = new Date(day.dt * 1000);
            const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
            
            dayElement.querySelector('.date').textContent = dayName;
            dayElement.querySelector('.max').textContent = `${Math.round(day.main.temp_max)}°`;
            dayElement.querySelector('.min').textContent = `${Math.round(day.main.temp_min)}°`;
            
            const img = dayElement.querySelector('img');
            img.src = `/plugins/weather-forecast/icons/${day.weather[0].description}.png`;
            img.alt = day.weather[0].description;
            img.onerror = () => img.src = '/plugins/weather-forecast/icons/clear.png';
        });
    }
    
    // Function to fetch weather data from the API
    function fetchWeatherData() {
        fetch('/api/plugins/weather-forecast/data')
            .then(response => response.json())
            .then(data => {
                if (data.current) {
                    const time = new Date(data.current.forecastTimeUtc);
                    timeElement.textContent = time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                    tempElement.textContent = `${Math.round(data.current.temperature)}° ${Math.round(data.current.feelsLike)}°`;
                    windElement.textContent = `${data.current.windSpeed} m/s ${data.current.precipitation} mm`;
                    pressureElement.textContent = `${data.current.pressure} hPa ${data.current.humidity}%`;
                    conditionElement.textContent = data.current.conditionCode;
                }
                
                if (data.daily) {
                    updateForecast(data.daily);
                }
            })
            .catch(() => {
                timeElement.textContent = 'Error';
                tempElement.textContent = 'Error';
                windElement.textContent = 'Error';
                pressureElement.textContent = 'Error';
                conditionElement.textContent = 'Error';
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 900;
    fetchWeatherData(); // Fetch data immediately
    setInterval(fetchWeatherData, refreshInterval * 1000);
} 