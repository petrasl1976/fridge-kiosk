document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('discord-channel-messages');
  if (!container) return;
  discordChannelInit(container);
});

function discordChannelInit(container) {
  // Gauti konfigūraciją ir spalvas
  const plugin = window.PLUGINS?.['discord-channel'] || {};
  const pluginConfig = plugin.config || {};
  const maxMessages = pluginConfig.format?.max_messages || 10;
  const usernameColors = window.KIOSK_CONFIG?.userColors || {};

  function fetchMessages() {
    fetch('/api/plugins/discord-channel/data')
      .then(r => r.json())
      .then(messages => {
        let html = "";
        if (Array.isArray(messages) && messages.length > 0) {
          // Imame tik maxMessages naujausių
          const lastMessages = messages.slice(0, maxMessages).reverse();
          lastMessages.forEach(msg => {
            const msgTime = new Date(msg.timestamp);
            const hh = String(msgTime.getHours()).padStart(2, '0');
            const mm = String(msgTime.getMinutes()).padStart(2, '0');
            const shortUsername = msg.author.username.substring(0, 2);
            const usernameColor = usernameColors[msg.author.username] || msg.color || '#888';
            html += `
              <div class="discord-message">
                ${hh}:${mm}
                <span class="discord-username" style="background-color: ${usernameColor};">${shortUsername}:</span>
                ${msg.content}
              </div>
            `;
          });
        } else {
          html = "<div>No new messages in channel</div>";
        }
        container.innerHTML = html;
      })
      .catch(e => {
        container.innerHTML = "Error loading messages.";
      });
  }

  fetchMessages();
  const refreshInterval = parseInt(pluginConfig.updateInterval) || 60;
  fetchMessages(); // Iškart gauti duomenis
  setInterval(fetchMessages, refreshInterval * 1000);
} 