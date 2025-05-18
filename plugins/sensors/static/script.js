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
    // Get plugin configuration
    const pluginObj = window.PLUGINS?.find(p => p.name === 'sensors');
    const pluginConfig = pluginObj?.config || {};
    const pluginData = window.PLUGINS_DATA?.['sensors']?.data || {};
    
    // DOM elements
    const temperatureElement = container.querySelector('#sensors-temperature');
    const humidityElement = container.querySelector('#sensors-humidity');
    const cpuTempElement = container.querySelector('#sensors-cpu-temp');
    
    // Display initial data
    if (pluginData.temperature) temperatureElement.textContent = `${pluginData.temperature}°C`;
    if (pluginData.humidity) humidityElement.textContent = `${pluginData.humidity}%`;
    if (pluginData.cpu_temp) cpuTempElement.textContent = `${pluginData.cpu_temp}°C`;
    
    // Set thresholds for warnings
    const thresholds = pluginConfig.thresholds || {
        temperature: {
            min_normal: 18, max_normal: 25
        },
        humidity: {
            min_normal: 40, max_normal: 60
        },
        cpu_temp: {
            warning: 60, critical: 70
        }
    };
    
    // Function to apply warning classes based on values
    function applyWarningClasses(element, value, min, max) {
        element.classList.remove('warning', 'critical');
        if (value < min || value > max) {
            element.classList.add('warning');
        }
    }
    
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
                    applyWarningClasses(
                        temperatureElement, 
                        data.temperature,
                        thresholds.temperature.min_normal, 
                        thresholds.temperature.max_normal
                    );
                }
                
                if (data.humidity) {
                    humidityElement.textContent = `${data.humidity}%`;
                    applyWarningClasses(
                        humidityElement, 
                        data.humidity,
                        thresholds.humidity.min_normal, 
                        thresholds.humidity.max_normal
                    );
                }
                
                if (data.cpu_temp) {
                    cpuTempElement.textContent = `${data.cpu_temp}°C`;
                    applyCpuTempWarning(
                        cpuTempElement, 
                        data.cpu_temp,
                        thresholds.cpu_temp.warning, 
                        thresholds.cpu_temp.critical
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