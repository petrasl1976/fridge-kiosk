/**
 * Sensors Plugin for Fridge Kiosk
 * Monitors temperature and humidity
 */

function sensorsInit() {
    // Get DOM elements
    const container = document.getElementById('sensors-container');
    const temperatureElement = document.getElementById('temperature-value');
    const humidityElement = document.getElementById('humidity-value');
    const statusElement = document.getElementById('sensor-status');
    const lastUpdateElement = document.getElementById('sensor-last-update');
    
    // Plugin state
    const state = {
        temperature: null,
        humidity: null,
        error: null,
        lastUpdate: null,
        updateInterval: 60000, // milliseconds
        warningThresholds: {
            temperature: {
                min: 1,
                max: 8
            },
            humidity: {
                min: 30,
                max: 50
            }
        },
        status: 'normal' // normal, warning, error
    };
    
    // Update status based on current readings
    function updateStatus() {
        if (state.error) {
            state.status = 'error';
            return;
        }
        
        // Check temperature
        if (state.temperature < state.warningThresholds.temperature.min || 
            state.temperature > state.warningThresholds.temperature.max) {
            state.status = 'warning';
            return;
        }
        
        // Check humidity
        if (state.humidity < state.warningThresholds.humidity.min || 
            state.humidity > state.warningThresholds.humidity.max) {
            state.status = 'warning';
            return;
        }
        
        state.status = 'normal';
    }
    
    // Display sensor readings on UI
    function displayReadings() {
        if (state.error) {
            temperatureElement.textContent = '—';
            humidityElement.textContent = '—';
            statusElement.textContent = state.error;
            statusElement.className = 'sensor-status error';
            container.classList.add('error');
            container.classList.remove('warning', 'normal');
        } else {
            // Update temperature
            temperatureElement.textContent = state.temperature;
            
            // Update humidity
            humidityElement.textContent = state.humidity;
            
            // Update status message
            if (state.status === 'normal') {
                statusElement.textContent = 'All readings normal';
                statusElement.className = 'sensor-status normal';
                container.classList.add('normal');
                container.classList.remove('warning', 'error');
            } else if (state.status === 'warning') {
                let message = '';
                if (state.temperature < state.warningThresholds.temperature.min) {
                    message += 'Temperature too low! ';
                } else if (state.temperature > state.warningThresholds.temperature.max) {
                    message += 'Temperature too high! ';
                }
                
                if (state.humidity < state.warningThresholds.humidity.min) {
                    message += 'Humidity too low! ';
                } else if (state.humidity > state.warningThresholds.humidity.max) {
                    message += 'Humidity too high! ';
                }
                
                statusElement.textContent = message;
                statusElement.className = 'sensor-status warning';
                container.classList.add('warning');
                container.classList.remove('normal', 'error');
            }
        }
        
        // Update last updated time
        if (state.lastUpdate) {
            const date = new Date(state.lastUpdate * 1000);
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');
            lastUpdateElement.textContent = `Updated: ${hours}:${minutes}`;
        } else {
            lastUpdateElement.textContent = 'Never updated';
        }
    }
    
    // Fetch sensor readings from backend API
    async function fetchSensorData() {
        try {
            const response = await fetch('/api/plugins/sensors/readings');
            const data = await response.json();
            
            // Check if there's an error from the API
            if (data.error) {
                state.error = data.error;
                state.temperature = null;
                state.humidity = null;
            } else {
                state.error = null;
                state.temperature = data.temperature;
                state.humidity = data.humidity;
            }
            
            state.lastUpdate = data.timestamp;
            
            // Update status and display
            updateStatus();
            displayReadings();
        } catch (error) {
            console.error('Error fetching sensor data:', error);
            state.error = 'Failed to connect to sensor service';
            state.status = 'error';
            displayReadings();
        }
    }
    
    // Initial delay to allow the page to load fully
    setTimeout(() => {
        // Load initial data
        fetchSensorData();
        
        // Set up regular updates
        setInterval(fetchSensorData, state.updateInterval);
    }, 500);
    
    // Return the public API of the plugin
    return {
        // Getter for current state
        getState: () => ({ ...state }),
        
        // Handle theme changes
        onThemeChange: (theme) => {
            // Theme-specific adaptations can be added here
            console.log(`Sensors plugin: Theme changed to ${theme}`);
        },
        
        // Handle orientation changes
        onOrientationChange: (orientation) => {
            // Orientation-specific adaptations can be added here
            console.log(`Sensors plugin: Orientation changed to ${orientation}`);
        },
        
        // System check to verify if data is stale
        checkSystem: () => {
            // Check if data is too old (more than 10 minutes)
            if (state.lastUpdate && (Date.now() / 1000 - state.lastUpdate > 600)) {
                return {
                    status: 'warning',
                    message: 'Sensor data is stale'
                };
            }
            
            return {
                status: state.status,
                message: state.error || 'Sensors operating normally'
            };
        }
    };
} 