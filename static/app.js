const statusEl = document.querySelector('#status');
const messagesEl = document.querySelector('#messages');
const formEl = document.querySelector('#chat-form');
const inputEl = document.querySelector('#message');

function addMessage(role, text) {
  const bubble = document.createElement('div');
  bubble.className = `message ${role}`;
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function loadStatus() {
  const response = await fetch('/api/status');
  const data = await response.json();
  if (data.configured) {
    statusEl.textContent = `Configured · model: ${data.model}`;
    statusEl.classList.remove('error');
    return;
  }
  statusEl.textContent = `Missing configuration: ${data.missing.join(', ')}`;
  statusEl.classList.add('error');
}

formEl.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;

  addMessage('user', message);
  inputEl.value = '';
  formEl.querySelector('button').disabled = true;

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Request failed');
    addMessage('assistant', data.reply);
  } catch (error) {
    addMessage('assistant', `Error: ${error.message}`);
  } finally {
    formEl.querySelector('button').disabled = false;
    inputEl.focus();
  }
});

addMessage('assistant', 'Hi! Send a message to test your configured assistant.');
loadStatus().catch((error) => {
  statusEl.textContent = `Status unavailable: ${error.message}`;
  statusEl.classList.add('error');
});
