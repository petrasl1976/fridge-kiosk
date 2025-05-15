/**
 * Sensors Plugin - JavaScript
 * 
 * This script handles updating sensor data and displaying it with appropriate styling.
 */

class SensorsPlugin {
    constructor() {
        this.config = null;
        this.refreshInterval = 60000; // Default: 60 seconds
        this.updateTimer = null;
        this.lastData = null;
        
        // DOM elements
        this.cpuTempContainer = document.getElementById('cpu-temp-container');
        this.cpuTempValue = document.getElementById('cpu-temp-value');
        this.roomTempContainer = document.getElementById('room-temp-container');
        this.roomTempValue = document.getElementById('room-temp-value');
        this.humidityContainer = document.getElementById('humidity-container');
        this.humidityValue = document.getElementById('humidity-value');
        
        // Initialize
        this.init();
    }
    
    /**
     * Initialize the plugin
     */
    init() {
        // Get initial configuration from the page
        if (window.pluginData && window.pluginData.sensors) {
            this.config = window.pluginData.sensors.config;
            this.lastData = window.pluginData.sensors.data;
            
            // Apply configuration
            this.applyConfig();
            
            // Update the display with initial data
            this.updateDisplay(this.lastData);
            
            // Start periodic updates
            this.startUpdates();
        } else {
            console.error('Sensors plugin: No configuration found');
        }
    }
    
    /**
     * Apply configuration settings
     */
    applyConfig() {
        // Set the refresh interval
        if (this.config && this.config.refresh_interval) {
            this.refreshInterval = this.config.refresh_interval * 1000; // Convert to milliseconds
        }
        
        // Show/hide CPU temperature
        if (this.config && this.cpuTempContainer) {
            this.cpuTempContainer.style.display = this.config.show_cpu_temp ? 'flex' : 'none';
        }
        
        // Show/hide room temperature
        if (this.config && this.roomTempContainer) {
            this.roomTempContainer.style.display = this.config.show_room_temp ? 'flex' : 'none';
        }
        
        // Show/hide humidity
        if (this.config && this.humidityContainer) {
            this.humidityContainer.style.display = this.config.show_humidity ? 'flex' : 'none';
        }
    }
    
    /**
     * Start periodic updates
     */
    startUpdates() {
        // Clear any existing timer
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        
        // Set up a new timer
        this.updateTimer = setInterval(() => {
            this.fetchData();
        }, this.refreshInterval);
        
        // Fetch data immediately
        this.fetchData();
    }
    
    /**
     * Fetch sensor data from the backend
     */
    fetchData() {
        fetch('/api/plugins/sensors/data')
            .then(response => response.json())
            .then(data => {
                this.lastData = data;
                this.updateDisplay(data);
            })
            .catch(error => {
                console.error('Error fetching sensor data:', error);
            });
    }
    
    /**
     * Update the display with the latest data
     */
    updateDisplay(data) {
        if (!data) return;
        
        // Update CPU temperature
        if (data.cpu_temp !== null && data.cpu_temp !== undefined) {
            this.cpuTempValue.textContent = data.cpu_temp;
            
            // Apply appropriate class based on thresholds
            this.cpuTempValue.className = this.getCpuTempClass(data.cpu_temp);
        } else {
            this.cpuTempValue.textContent = '--';
            this.cpuTempValue.className = 'temp-normal';
        }
        
        // Update room temperature
        if (data.temperature !== null && data.temperature !== undefined) {
            this.roomTempValue.textContent = data.temperature;
            
            // Apply appropriate class based on thresholds
            this.roomTempValue.className = this.getRoomTempClass(data.temperature);
        } else {
            this.roomTempValue.textContent = '--';
            this.roomTempValue.className = 'room-temp-normal';
        }
        
        // Update humidity
        if (data.humidity !== null && data.humidity !== undefined) {
            this.humidityValue.textContent = data.humidity;
            
            // Apply appropriate class based on thresholds
            this.humidityValue.className = this.getHumidityClass(data.humidity);
        } else {
            this.humidityValue.textContent = '--';
            this.humidityValue.className = 'humid-normal';
        }
    }
    
    /**
     * Get the CSS class for CPU temperature based on thresholds
     */
    getCpuTempClass(temp) {
        if (!this.config || !this.config.thresholds || !this.config.thresholds.cpu_temp) {
            return 'temp-normal';
        }
        
        const thresholds = this.config.thresholds.cpu_temp;
        
        if (temp >= thresholds.critical) {
            return 'temp-critical';
        } else if (temp >= thresholds.warning) {
            return 'temp-warning';
        } else {
            return 'temp-normal';
        }
    }
    
    /**
     * Get the CSS class for room temperature based on thresholds
     */
    getRoomTempClass(temp) {
        if (!this.config || !this.config.thresholds || !this.config.thresholds.temperature) {
            return 'room-temp-normal';
        }
        
        const thresholds = this.config.thresholds.temperature;
        
        if (temp < thresholds.min_warning || temp > thresholds.max_warning) {
            return 'room-temp-critical';
        } else if (temp < thresholds.min_normal || temp > thresholds.max_normal) {
            return 'room-temp-warning';
        } else {
            return 'room-temp-normal';
        }
    }
    
    /**
     * Get the CSS class for humidity based on thresholds
     */
    getHumidityClass(humidity) {
        if (!this.config || !this.config.thresholds || !this.config.thresholds.humidity) {
            return 'humid-normal';
        }
        
        const thresholds = this.config.thresholds.humidity;
        
        if (humidity < thresholds.min_warning || humidity > thresholds.max_warning) {
            return 'humid-critical';
        } else if (humidity < thresholds.min_normal || humidity > thresholds.max_normal) {
            return 'humid-warning';
        } else {
            return 'humid-normal';
        }
    }
}

// Initialize the plugin when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.sensorsPlugin = new SensorsPlugin();
}); 