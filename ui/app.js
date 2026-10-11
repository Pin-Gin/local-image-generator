const profileSelect = document.getElementById('profile');
const form = document.getElementById('chat-form');
const promptInput = document.getElementById('prompt');
const messages = document.getElementById('messages');
const jsonPreview = document.getElementById('json-preview');
const generateButton = document.getElementById('generate-button');
const jsonButton = document.getElementById('json-button');
const generationStatus = document.getElementById('generation-status');
const generatedImage = document.getElementById('generated-image');
const generationMeta = document.getElementById('generation-meta');
const seedModeSelect = document.getElementById('seed-mode');
const seedValueInput = document.getElementById('seed-value');

function addMessage(text, role) {
  const node = document.createElement('div');
  node.className = `message ${role}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

function describeIntent(intent) {
  if (!intent || typeof intent !== 'object') {
    return 'Generation Request JSONを作成しました。';
  }
  if (intent.status === 'needs_confirmation') {
    return '入力に複数候補があるため確認が必要です。JSONを確認してください。';
  }
  if (intent.status === 'unparsed') {
    return '登録済み辞書に一致する条件がありません。画像生成にはparsed intentが必要です。';
  }
  const resolved = [];
  for (const key of ['character', 'outfit', 'background', 'pose', 'expression', 'hair', 'rendering']) {
    if (intent[key]) resolved.push(`${key}=${intent[key]}`);
  }
  const suffix = resolved.length ? ` (${resolved.join(', ')})` : '';
  return `入力内容を内部JSONへ正規化しました${suffix}。`;
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

function currentInput() {
  const userText = promptInput.value.trim();
  const profileId = profileSelect.value;
  const seedMode = seedModeSelect.value;
  if (!userText) throw new Error('生成内容を入力してください。');
  if (!profileId) throw new Error('Profileを選択してください。');

  let seed = null;
  if (seedMode === 'FIXED') {
    const raw = seedValueInput.value.trim();
    if (!/^\d+$/.test(raw)) throw new Error('Fixed Seedは0以上の整数を入力してください。');
    seed = Number(raw);
    if (!Number.isSafeInteger(seed) || seed < 0) {
      throw new Error('Fixed SeedはJavaScriptで安全に扱える0以上の整数を入力してください。');
    }
  }

  return {userText, profileId, seedMode, seed};
}

async function postChat(path, input) {
  const response = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_text: input.userText,
      profile_id: input.profileId,
      seed_mode: input.seedMode,
      seed: input.seed,
    }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

seedModeSelect.addEventListener('change', () => {
  seedValueInput.disabled = seedModeSelect.value !== 'FIXED';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const input = currentInput();
    addMessage(input.userText, 'user');
    const payload = await postChat('/api/chat/request', input);
    jsonPreview.textContent = JSON.stringify(payload.request, null, 2);
    addMessage(describeIntent(payload.request.intent), 'assistant');
  } catch (error) {
    addMessage(`エラー: ${error.message}`, 'system');
  }
});

generateButton.addEventListener('click', async () => {
  let input;
  try {
    input = currentInput();
  } catch (error) {
    addMessage(`エラー: ${error.message}`, 'system');
    return;
  }

  addMessage(input.userText, 'user');
  generationStatus.textContent = '生成中...';
  generationMeta.textContent = '';
  generatedImage.hidden = true;
  jsonButton.disabled = true;
  generateButton.disabled = true;

  try {
    const payload = await postChat('/api/chat/generate', input);
    jsonPreview.textContent = JSON.stringify(payload.request, null, 2);
    const generation = payload.generation;
    generatedImage.src = `${generation.output_url}?t=${Date.now()}`;
    generatedImage.hidden = false;
    generationStatus.textContent = `生成完了: ${generation.generation_id}`;
    generationMeta.textContent = JSON.stringify(generation, null, 2);
    addMessage(
      `画像を生成しました。generation_id=${generation.generation_id}, seed=${generation.seed}`,
      'assistant',
    );
  } catch (error) {
    generationStatus.textContent = '生成失敗';
    addMessage(`生成エラー: ${error.message}`, 'system');
  } finally {
    jsonButton.disabled = false;
    generateButton.disabled = false;
  }
});

loadProfiles().catch((error) => {
  addMessage(`Profile読込エラー: ${error.message}`, 'system');
});
