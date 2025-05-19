document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('discord-channel-messages');
  if (!container) return;
  discordChannelInit(container);
});

function discordChannelInit(container) {
  // Get plugin configuration
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
          // Filter messages from last 6 hours
          const sixHoursAgo = Date.now() - 6 * 3600 * 1000;
          const recentMessages = messages.filter(msg => new Date(msg.timestamp) >= sixHoursAgo);

          if (recentMessages.length > 0) {
            // Take only the latest maxMessages
            const lastMessages = recentMessages.slice(0, maxMessages).reverse();
            lastMessages.forEach(msg => {
              const msgTime = new Date(msg.timestamp);
              // +2 hours (simple correction, not accounting for DST)
              msgTime.setHours(msgTime.getHours() + 2);

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
        } else {
          html = "<div>No messages available</div>";
        }
        container.innerHTML = html;
      })
      .catch(() => {
        container.innerHTML = "Error loading messages.";
      });
  }

  // Initial fetch and setup periodic updates
  fetchMessages();
  const refreshInterval = parseInt(pluginConfig.updateInterval) || 60;
  setInterval(fetchMessages, refreshInterval * 1000);
} 