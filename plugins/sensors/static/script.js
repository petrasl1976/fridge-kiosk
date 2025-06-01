/**
 * Sensors Plugin - Displays temperature, humidity and CPU temperature
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('sensors');
    if (!container) return;
    
    // Initialize
    sensorsInit(container);
});

function sensorsInit(container) {
    // Get plugin configuration
    const plugin = window.PLUGINS?.['sensors'] || {};
    const pluginConfig = plugin.config || {};
    
    // DOM elements
    const tempElement = container.querySelector('#sensors-temperature');
    const humidityElement = container.querySelector('#sensors-humidity');
    const cpuTempElement = container.querySelector('#sensors-cpu-temp');
    
    // Function to update CPU temperature color
    function updateCpuTempColor(temp) {
        cpuTempElement.classList.remove('normal', 'warning', 'critical');
        if (temp >= 70) {
            cpuTempElement.classList.add('critical');
        } else if (temp >= 60) {
            cpuTempElement.classList.add('warning');
        } else {
            cpuTempElement.classList.add('normal');
        }
    }
    
    // Function to fetch sensor data from the API
    function fetchSensorData() {
        fetch('/api/plugins/sensors/data')
            .then(response => response.json())
            .then(data => {
                if (data.temperature) tempElement.textContent = `${data.temperature}°C`;
                if (data.humidity) humidityElement.textContent = `${data.humidity}%`;
                if (data.cpu_temp) {
                    cpuTempElement.textContent = `${data.cpu_temp}°C`;
                    updateCpuTempColor(data.cpu_temp);
                }
            })
            .catch(() => {
                tempElement.textContent = 'Error';
                humidityElement.textContent = 'Error';
                cpuTempElement.textContent = 'Error';
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 30;
    fetchSensorData(); // Fetch data immediately
    setInterval(fetchSensorData, refreshInterval * 1000);
} 