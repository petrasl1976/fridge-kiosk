/**
 * Diagnostics tool for debugging Fridge Kiosk configuration
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Diagnostics script loaded');

    // Create diagnostic display
    const diagnosticsContainer = document.createElement('div');
    diagnosticsContainer.style.position = 'fixed';
    diagnosticsContainer.style.top = '10px';
    diagnosticsContainer.style.left = '10px';
    diagnosticsContainer.style.backgroundColor = 'rgba(0,0,0,0.8)';
    diagnosticsContainer.style.color = 'white';
    diagnosticsContainer.style.padding = '10px';
    diagnosticsContainer.style.fontSize = '12px';
    diagnosticsContainer.style.fontFamily = 'monospace';
    diagnosticsContainer.style.zIndex = '99999';
    diagnosticsContainer.style.maxWidth = '500px';
    diagnosticsContainer.style.maxHeight = '80vh';
    diagnosticsContainer.style.overflow = 'auto';
    
    // Add diagnostic data
    let diagnosticHtml = `<h3>Kiosk Diagnostics</h3>`;
    
    // Plugin data check
    if (window.PLUGINS) {
        const dateTimePlugin = window.PLUGINS.find(p => p.name === 'date-time');
        if (dateTimePlugin) {
            diagnosticHtml += `<h4>date-time plugin found:</h4>`;
            diagnosticHtml += `<pre>${JSON.stringify(dateTimePlugin, null, 2)}</pre>`;
            
            if (dateTimePlugin.config) {
                diagnosticHtml += `<h4>UpdateInterval:</h4>`;
                diagnosticHtml += `<pre>Value: ${dateTimePlugin.config.updateInterval}
Type: ${typeof dateTimePlugin.config.updateInterval}</pre>`;
            } else {
                diagnosticHtml += `<p>No config in date-time plugin!</p>`;
            }
        } else {
            diagnosticHtml += `<p>date-time plugin not found in PLUGINS!</p>`;
        }
    } else {
        diagnosticHtml += `<p>No PLUGINS object found!</p>`;
    }
    
    // Global config data
    diagnosticHtml += `<h4>KIOSK_CONFIG:</h4>`;
    diagnosticHtml += `<pre>${JSON.stringify(window.KIOSK_CONFIG, null, 2)}</pre>`;
    
    // Browser info
    diagnosticHtml += `<h4>Browser Info:</h4>`;
    diagnosticHtml += `<pre>User Agent: ${navigator.userAgent}
Window Size: ${window.innerWidth} x ${window.innerHeight}
Orientation: ${window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'}</pre>`;
    
    // Add close button
    diagnosticHtml += `<button id="close-diagnostics" style="margin-top:10px;padding:5px;">Close</button>`;
    
    // Set content and add to body
    diagnosticsContainer.innerHTML = diagnosticHtml;
    document.body.appendChild(diagnosticsContainer);
    
    // Handle close button click
    document.getElementById('close-diagnostics').addEventListener('click', function() {
        document.body.removeChild(diagnosticsContainer);
    });
}); 