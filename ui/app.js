const profileSelect = document.getElementById('profile');
const form = document.getElementById('chat-form');
const promptInput = document.getElementById('prompt');
const messages = document.getElementById('messages');
const jsonPreview = document.getElementById('json-preview');

function addMessage(text, role) {
  const node = document.createElement('div');
  node.className = `message ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

async function loadProfiles() {
  const response = await fetch('/api/profiles');
  if (!response.ok) throw new Error(`profiles HTTP ${response.status}`);
  const payload = await response.json();
  profileSelect.replaceChildren();
  for (const profileId of payload.profiles || []) {
    const option = document.createElement('option');
    option.value = profileId;
    option.textContent = profileId;
    profileSelect.appendChild(option);
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const userText = promptInput.value.trim();
  const profileId = profileSelect.value;
  if (!userText) return;

  addMessage(userText, 'user');
  promptInput.value = '';

  try {
    const response = await fetch('/api/chat/request', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({user_text: userText, profile_id: profileId}),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);

    jsonPreview.textContent = JSON.stringify(payload.request, null, 2);
    addMessage('Generation Request JSONを作成しました。まだ画像生成には接続していません。', 'assistant');
  } catch (error) {
    addMessage(`エラー: ${error.message}`, 'system');
  }
});

loadProfiles().catch((error) => {
  addMessage(`Profile読込エラー: ${error.message}`, 'system');
});
