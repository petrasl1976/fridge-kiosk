/**
 * Sensors Plugin for Fridge Kiosk
 * Monitors temperature and humidity
 */

// Initialize the sensors plugin
function sensorsInit(config, container) {
    console.log('Initializing Sensors plugin with config:', config);
    
    // DOM elements
    const tempElement = container.querySelector('.temperature');
    const humidityElement = container.querySelector('.humidity');
    const statusElement = container.querySelector('.status-value');
    
    // Plugin state
    const state = {
        temperature: null,
        humidity: null,
        lastUpdate: null,
        updateInterval: config.updateInterval || 30, // seconds
        warningThresholds: config.warningThresholds || {
            temperature: { min: 2, max: 8 },
            humidity: { min: 30, max: 60 }
        },
        status: 'initializing'
    };
    
    // For demo purposes - simulate sensor readings
    function simulateSensorReadings() {
        // Simulate temperature between 1 and 10°C with occasional outliers
        state.temperature = Math.random() < 0.1 
            ? Math.random() * 15 - 2  // Occasional outlier between -2 and 13
            : Math.random() * 7 + 2;  // Usually between 2 and 9
            
        // Simulate humidity between 20 and 70% with occasional outliers
        state.humidity = Math.random() < 0.1
            ? Math.random() * 80 + 10  // Occasional outlier between 10 and 90
            : Math.random() * 30 + 30; // Usually between 30 and 60
            
        state.lastUpdate = new Date();
        
        // Update status based on readings
        updateStatus();
        
        // Format and display readings
        displayReadings();
    }
    
    // Update status based on current readings
    function updateStatus() {
        const { temperature, humidity, warningThresholds } = state;
        
        if (temperature === null || humidity === null) {
            state.status = 'no data';
            return;
        }
        
        const tempOk = temperature >= warningThresholds.temperature.min && 
                        temperature <= warningThresholds.temperature.max;
        
        const humidityOk = humidity >= warningThresholds.humidity.min && 
                           humidity <= warningThresholds.humidity.max;
        
        if (tempOk && humidityOk) {
            state.status = 'normal';
        } else if (!tempOk && humidityOk) {
            state.status = temperature < warningThresholds.temperature.min 
                ? 'temperature too low' 
                : 'temperature too high';
        } else if (tempOk && !humidityOk) {
            state.status = humidity < warningThresholds.humidity.min 
                ? 'humidity too low' 
                : 'humidity too high';
        } else {
            state.status = 'critical - multiple warnings';
        }
    }
    
    // Format and display readings on the UI
    function displayReadings() {
        if (state.temperature !== null) {
            tempElement.textContent = `${state.temperature.toFixed(1)} °C`;
            
            // Apply warning classes
            tempElement.classList.remove('warning', 'critical');
            if (state.temperature < state.warningThresholds.temperature.min ||
                state.temperature > state.warningThresholds.temperature.max) {
                tempElement.classList.add(
                    state.temperature < state.warningThresholds.temperature.min - 2 ||
                    state.temperature > state.warningThresholds.temperature.max + 2 
                        ? 'critical' : 'warning'
                );
            }
        }
        
        if (state.humidity !== null) {
            humidityElement.textContent = `${state.humidity.toFixed(1)} %`;
            
            // Apply warning classes
            humidityElement.classList.remove('warning', 'critical');
            if (state.humidity < state.warningThresholds.humidity.min ||
                state.humidity > state.warningThresholds.humidity.max) {
                humidityElement.classList.add(
                    state.humidity < state.warningThresholds.humidity.min - 10 ||
                    state.humidity > state.warningThresholds.humidity.max + 10 
                        ? 'critical' : 'warning'
                );
            }
        }
        
        // Update status text
        statusElement.textContent = state.status.charAt(0).toUpperCase() + state.status.slice(1);
        
        // Update status classes
        statusElement.classList.remove('status-normal', 'status-warning', 'status-critical');
        if (state.status === 'normal') {
            statusElement.classList.add('status-normal');
        } else if (state.status.includes('critical')) {
            statusElement.classList.add('status-critical');
        } else {
            statusElement.classList.add('status-warning');
        }
    }
    
    // Start the update cycle
    statusElement.textContent = 'Connecting to sensors...';
    
    // Simulate initial delay for connecting to sensors
    setTimeout(() => {
        simulateSensorReadings();
        // Set up regular updates
        setInterval(simulateSensorReadings, state.updateInterval * 1000);
    }, 2000);
    
    // Return the public API
    return {
        getState: () => ({ ...state }),
        onThemeChange: (theme) => {
            console.log('Sensors plugin: Theme changed to', theme);
            // Handle theme change if needed
        },
        onOrientationChange: (orientation) => {
            console.log('Sensors plugin: Orientation changed to', orientation);
            // Handle orientation change if needed
        },
        onSystemCheck: () => {
            // Check if data is stale
            if (state.lastUpdate && Date.now() - state.lastUpdate.getTime() > state.updateInterval * 2000) {
                console.warn('Sensors plugin: Data is stale');
                state.status = 'sensor connection lost';
                statusElement.textContent = 'Sensor connection lost';
                statusElement.classList.remove('status-normal', 'status-warning');
                statusElement.classList.add('status-critical');
            }
        }
    };
} 