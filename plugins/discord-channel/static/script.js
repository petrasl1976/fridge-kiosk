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
  console.debug("Available usernameColors:", usernameColors);

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

              // Use first two letters (uppercased) for color key, like calendar
              const shortUsername = msg.author.username.substring(0, 2).toUpperCase();
              const usernameColor = usernameColors[shortUsername] || "#673AB7"; // Use purple as default
              console.debug(`Username: ${msg.author.username}, Short: ${shortUsername}, Color: ${usernameColor}`);

              // Handle message content as image if it's a direct image/gif link or Tenor/Giphy
              let contentHtml = msg.content;
              const imageUrlRegex = /(https?:\/\/.*\.(?:png|jpg|jpeg|gif|webp))/i;
              const tenorGiphyRegex = /(https?:\/\/(?:media\\.)?(?:tenor|giphy)\\.com\/[^\s]+)/i;

              if (imageUrlRegex.test(msg.content.trim())) {
                contentHtml = `
                  <div class="discord-image-container">
                    <img src="${msg.content.trim()}" alt="Discord image link" />
                  </div>
                `;
              } else if (tenorGiphyRegex.test(msg.content.trim())) {
                contentHtml = `
                  <div class="discord-image-container">
                    <img src="${msg.content.trim()}" alt="Discord gif link" />
                  </div>
                `;
              }

              // Handle attachments
              let attachmentsHtml = '';
              if (msg.attachments && msg.attachments.length > 0) {
                msg.attachments.forEach(attachment => {
                  if (attachment.content_type && attachment.content_type.startsWith('image/')) {
                    attachmentsHtml += `
                      <div class="discord-image-container">
                        <img src="${attachment.url}" alt="Discord attachment" />
                      </div>
                    `;
                  }
                });
              }

              // Handle embeds
              let embedsHtml = '';
              if (msg.embeds && msg.embeds.length > 0) {
                msg.embeds.forEach(embed => {
                  if (embed.image && embed.image.url) {
                    embedsHtml += `
                      <div class="discord-image-container">
                        <img src="${embed.image.url}" alt="Discord embed image" />
                      </div>
                    `;
                  }
                  if (embed.thumbnail && embed.thumbnail.url) {
                    embedsHtml += `
                      <div class="discord-image-container">
                        <img src="${embed.thumbnail.url}" alt="Discord embed thumbnail" />
                      </div>
                    `;
                  }
                });
              }

              html += `
                <div class="discord-message">
                  ${hh}:${mm}
                  <span class="discord-username" style="background-color: ${usernameColor}; color: white;">${shortUsername}:</span>
                  ${contentHtml}
                  ${attachmentsHtml}
                  ${embedsHtml}
                </div>
              `;
            });
          } else {
            html = "<div>...</div>";
          }
        } else {
          html = "<div>No messages available</div>";
        }
        container.innerHTML = html;
      })
      .catch(error => {
        console.error("Error fetching messages:", error);
        container.innerHTML = "Error loading messages.";
      });
  }

  // Initial fetch and setup periodic updates
  fetchMessages();
  const refreshInterval = parseInt(pluginConfig.updateInterval) || 60;
  setInterval(fetchMessages, refreshInterval * 1000);
} 