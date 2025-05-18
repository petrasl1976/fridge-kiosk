/**
 * Sensors Plugin - Displays temperature, humidity and CPU temperature
 */

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('plugin-sensors');
    if (!container) return;
    
    // Initialize
    sensorsInit(container);
});

function sensorsInit(container) {
    // Get plugin configuration and data
    const plugin = window.PLUGINS?.['sensors'] || {};
    const pluginConfig = plugin.config || {};
    const pluginData = plugin.data || {};
    
    // DOM elements
    const temperatureElement = container.querySelector('#sensors-temperature');
    const humidityElement = container.querySelector('#sensors-humidity');
    const cpuTempElement = container.querySelector('#sensors-cpu-temp');
    const sensorReadings = container.querySelector('.sensor-readings');
    
    // Apply font size from config
    sensorReadings.style.cssText += `font-size: ${pluginConfig.format.font_size} !important;`;
    
    // Display initial data
    if (pluginData.temperature) temperatureElement.textContent = `${pluginData.temperature}°C`;
    if (pluginData.humidity) humidityElement.textContent = `${pluginData.humidity}%`;
    if (pluginData.cpu_temp) cpuTempElement.textContent = `${pluginData.cpu_temp}°C`;
    
    // Set thresholds for CPU temperature warnings
    const cpuThresholds = pluginConfig.thresholds?.cpu_temp || {
        warning: 60,
        critical: 70
    };
    
    // Function to apply CPU temperature warning classes
    function applyCpuTempWarning(element, value, warning, critical) {
        element.classList.remove('warning', 'critical');
        if (value >= critical) {
            element.classList.add('critical');
        } else if (value >= warning) {
            element.classList.add('warning');
        }
    }
    
    // Function to fetch sensor data from the API
    function fetchSensorData() {
        fetch('/api/plugins/sensors/data')
            .then(response => response.json())
            .then(data => {
                if (data.temperature) {
                    temperatureElement.textContent = `${data.temperature}°C`;
                }
                
                if (data.humidity) {
                    humidityElement.textContent = `${data.humidity}%`;
                }
                
                if (data.cpu_temp) {
                    cpuTempElement.textContent = `${data.cpu_temp}°C`;
                    applyCpuTempWarning(
                        cpuTempElement, 
                        data.cpu_temp,
                        cpuThresholds.warning, 
                        cpuThresholds.critical
                    );
                }
            })
            .catch(() => {
                temperatureElement.classList.add('error');
                humidityElement.classList.add('error');
                cpuTempElement.classList.add('error');
            });
    }
    
    // Set up automatic refresh from API
    const refreshInterval = parseInt(pluginConfig.updateInterval) || 30;
    setInterval(fetchSensorData, refreshInterval * 1000);
} 