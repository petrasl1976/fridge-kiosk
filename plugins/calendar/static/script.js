/**
 * Calendar Statusbar Plugin - Shows current time and sensor stats (CPU, temp, humidity)
 * Combines functionality of date-time (time computed on front-end) and sensors (data fetched via API).
 */

(function () {
  document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('calendar');
    if (!container) return;
    calendarInit(container);
  });

  function calendarInit(container) {
    const plugin = window.PLUGINS?.['calendar'] || {};
    const pluginConfig = plugin.config || {};

    // Element refs
    const cpuEl = container.querySelector('#cpu_text');
    const tempEl = container.querySelector('#thermometer_text');
    const humidityEl = container.querySelector('#humidity_text');
    const timeEl = container.querySelector('#time_text');

    /* ---------- TIME ----------- */
    function updateTime() {
      const now = new Date();
      // YYYY-MM-DD | HH:MM:SS format
      const pad = (n) => n.toString().padStart(2, '0');
      const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
      const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
      timeEl.textContent = `${dateStr} | ${timeStr}`;
    }
    updateTime();
    setInterval(updateTime, 1000);

    /* ---------- SENSOR DATA ----------- */
    function updateCpuTempColor(temp) {
      if (!cpuEl) return;
      cpuEl.classList.remove('normal', 'warning', 'critical');
      if (temp >= 70) {
        cpuEl.classList.add('critical');
      } else if (temp >= 60) {
        cpuEl.classList.add('warning');
      } else {
        cpuEl.classList.add('normal');
      }
    }

    function populateSensorData(data) {
      if (data.cpu_temp !== null && data.cpu_temp !== undefined) {
        cpuEl.textContent = `${data.cpu_temp}°C`;
        updateCpuTempColor(data.cpu_temp);
      }
      if (data.temperature !== null && data.temperature !== undefined) {
        tempEl.textContent = `${data.temperature}°C`;
      }
      if (data.humidity !== null && data.humidity !== undefined) {
        humidityEl.textContent = `${data.humidity}%`;
      }
    }

    function fetchSensorData() {
      fetch('/api/plugins/calendar/data')
        .then((r) => r.json())
        .then(populateSensorData)
        .catch((err) => {
          console.error('Calendar plugin sensor fetch error', err);
          cpuEl.textContent = tempEl.textContent = humidityEl.textContent = '—';
        });
    }

    const refresh = parseInt(pluginConfig.updateInterval, 10) || 30;
    fetchSensorData();
    setInterval(fetchSensorData, refresh * 1000);
  }
})(); 