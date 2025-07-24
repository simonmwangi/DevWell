// assistant_chat.js

(function () {
  const toggleBtn = document.createElement('button');
  toggleBtn.id = 'assistant-toggle';
  toggleBtn.innerHTML = '<i class="fas fa-comment-dots"></i>';
  document.body.appendChild(toggleBtn);

  const chatBox = document.createElement('div');
  chatBox.id = 'assistant-chat-box';
  chatBox.innerHTML = `
    <div id="assistant-header">
      <span>DevWell Assistant</span>
      <button id="assistant-close">&times;</button>
    </div>
    <div id="assistant-messages"></div>
    <form id="assistant-form">
      <input type="text" id="assistant-input" placeholder="Ask me anything..." autocomplete="off" />
      <button type="submit"><i class="fas fa-paper-plane"></i></button>
    </form>`;
  document.body.appendChild(chatBox);

  // CSS classes handled by assistant_chat.css

  let reindexed = false;

  function formatText(text) {
    // Convert * bullet points to <ul><li>...</li></ul>
    let html = text
      .replace(/\n?\* (.+)/g, '<li>$1</li>')          // list items
      .replace(/(Answer:|Response:)/g, '<strong>$1</strong>')  // emphasize answer
      .replace(/\n{2,}/g, '</ul><br><ul>');            // support breaks between lists
  
    // Wrap with <ul> if there are <li>
    if (html.includes('<li>')) html = `<ul>${html}</ul>`;
  
    return html;
  }
  
  function appendMessage(text, from) {
    const msg = document.createElement('div');
    msg.className = `assistant-msg ${from}`;
    msg.innerHTML = formatText(text); // use innerHTML to support formatting
    document.getElementById('assistant-messages').appendChild(msg);
    msg.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }

  function getCsrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  async function triggerReindex() {
    try {
      await fetch('/assistant/reindex', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrf() },
        credentials: 'same-origin',
      });
    } catch (e) {
      console.warn('Reindex failed', e);
    }
  }

  toggleBtn.addEventListener('click', () => {
    const opened = chatBox.classList.toggle('open');
    if (opened && !reindexed) {
      reindexed = true;
      triggerReindex();
    }
  });

  document.getElementById('assistant-close').addEventListener('click', () => {
    chatBox.classList.remove('open');
  });

  document.getElementById('assistant-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('assistant-input');
    const text = input.value.trim();
    if (!text) return;
    appendMessage(text, 'user');
    input.value = '';

    try {
      const csrf = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      const res = await fetch('/assistant/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf,
        },
        credentials: 'same-origin',
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      appendMessage(data.answer || 'Sorry, I had trouble answering.', 'bot');
    } catch (err) {
        console.log(err)
      appendMessage('Error contacting assistant.', 'bot');
    }
  });
})();
