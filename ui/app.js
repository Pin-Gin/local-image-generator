const appShell = document.getElementById('app-shell');
const profileSelect = document.getElementById('profile');
const form = document.getElementById('chat-form');
const promptInput = document.getElementById('prompt');
const jsonPreview = document.getElementById('json-preview');
const generateButton = document.getElementById('generate-button');
const generationStatus = document.getElementById('generation-status');
const generatedImage = document.getElementById('generated-image');
const imagePlaceholder = document.getElementById('image-placeholder');
const generationMeta = document.getElementById('generation-meta');
const seedModeSelect = document.getElementById('seed-mode');
const seedValueInput = document.getElementById('seed-value');
const toolButtons = [...document.querySelectorAll('.tool-button')];
const sidePanels = [...document.querySelectorAll('.side-panel')];

const modeButton = document.getElementById('mode-button');
const modeButtonTitle = document.getElementById('mode-button-title');
const modeMenu = document.getElementById('mode-menu');
const modeOptions = [...document.querySelectorAll('.mode-option')];
const modeViews = [...document.querySelectorAll('.mode-view')];
const workspaceTitle = document.getElementById('workspace-title');
const workspaceDescription = document.getElementById('workspace-description');

const learnStatus = document.getElementById('learn-ai-status');
const learnImageInput = document.getElementById('learn-image-input');
const learnImageRemove = document.getElementById('learn-image-remove');
const learnImageWrap = document.getElementById('learn-image-wrap');
const learnImagePreview = document.getElementById('learn-image-preview');
const learnImageName = document.getElementById('learn-image-name');
const learnUploadCopy = document.getElementById('learn-upload-copy');
const learnForm = document.getElementById('learn-form');
const learnPrompt = document.getElementById('learn-prompt');
const learnSend = document.getElementById('learn-send');
const learnChatLog = document.getElementById('learn-chat-log');

const devStatus = document.getElementById('dev-ai-status');
const devForm = document.getElementById('dev-form');
const devPrompt = document.getElementById('dev-prompt');
const devSend = document.getElementById('dev-send');
const devChatLog = document.getElementById('dev-chat-log');

const modeMeta = {
  generate: {
    title: '画像生成',
    description: '自然言語またはJSONを入力して画像を生成します。',
    view: 'generate-view',
  },
  learn: {
    title: '学習',
    description: 'ローカルAIで画像を解析し、学習対象を切り分けます。',
    view: 'learn-view',
  },
  dev: {
    title: '開発',
    description: 'ローカルAIでコード修正指示を解析します。',
    view: 'dev-view',
  },
};

const localHistories = {learn: [], dev: []};
let currentMode = 'generate';
let learnImageBase64 = null;
let learnImageDataUrl = null;

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

async function postGenerate(input) {
  const response = await fetch('/api/chat/generate', {
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

async function loadLocalAIStatus(role) {
  const statusElement = role === 'learn' ? learnStatus : devStatus;
  statusElement.textContent = '確認中...';
  statusElement.className = 'status-pill';

  try {
    const response = await fetch('/api/local-ai/status', {cache: 'no-store'});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);

    const roleInfo = payload.local_ai?.roles?.[role];
    if (!roleInfo) throw new Error(`${role} role unavailable`);

    if (!roleInfo.installed) {
      statusElement.textContent = `モデル未導入: ${roleInfo.model}`;
      statusElement.classList.add('warning');
      return false;
    }

    statusElement.textContent = `オンライン: ${roleInfo.model}`;
    statusElement.classList.add('online');
    return true;
  } catch (error) {
    statusElement.textContent = `オフライン: ${error.message}`;
    statusElement.classList.add('error');
    return false;
  }
}

async function postLocalAI(role, message, history, images = []) {
  const response = await fetch('/api/local-ai/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({role, message, history, images}),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  const result = payload.local_ai;
  if (!result || typeof result.content !== 'string' || !result.content.trim()) {
    throw new Error('ローカルAIから本文が返りませんでした。');
  }
  return result;
}

function showSidePanel(panelId) {
  sidePanels.forEach((panel) => panel.classList.toggle('hidden', panel.id !== panelId));
  toolButtons.forEach((button) => button.classList.toggle('active', button.dataset.panel === panelId));
}

function closeModeMenu() {
  modeMenu.classList.add('hidden');
  modeButton.setAttribute('aria-expanded', 'false');
}

function setMode(mode) {
  if (!modeMeta[mode]) return;
  currentMode = mode;
  const meta = modeMeta[mode];
  appShell.classList.toggle('generation-mode', mode === 'generate');
  appShell.classList.toggle('ai-mode', mode !== 'generate');
  modeButtonTitle.textContent = meta.title;
  workspaceTitle.textContent = meta.title;
  workspaceDescription.textContent = meta.description;

  modeViews.forEach((view) => view.classList.toggle('hidden', view.id !== meta.view));
  modeOptions.forEach((option) => option.classList.toggle('selected', option.dataset.mode === mode));
  closeModeMenu();

  if (mode === 'learn') loadLocalAIStatus('learn');
  if (mode === 'dev') loadLocalAIStatus('dev');
}

function appendChatMessage(container, role, text, imageUrl = null) {
  const item = document.createElement('div');
  item.className = `chat-message ${role}`;

  const roleLabel = document.createElement('div');
  roleLabel.className = 'chat-role';
  roleLabel.textContent = role === 'user' ? 'あなた' : 'ローカルAI';
  item.appendChild(roleLabel);

  if (imageUrl) {
    const image = document.createElement('img');
    image.className = 'chat-image';
    image.src = imageUrl;
    image.alt = 'Attached image';
    item.appendChild(image);
  }

  const body = document.createElement('div');
  body.className = 'chat-body';
  body.textContent = text;
  item.appendChild(body);
  container.appendChild(item);
  container.scrollTop = container.scrollHeight;
}

function resetLearnImage() {
  learnImageBase64 = null;
  learnImageDataUrl = null;
  learnImageInput.value = '';
  learnImagePreview.removeAttribute('src');
  learnImageWrap.hidden = true;
  learnImageRemove.hidden = true;
  learnImageName.textContent = '';
  learnUploadCopy.textContent = '画像を選択';
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('画像を読み込めませんでした。'));
    reader.readAsDataURL(file);
  });
}

async function handleLocalSubmit({role, promptElement, buttonElement, logElement}) {
  const message = promptElement.value.trim();
  if (!message) return;

  const online = await loadLocalAIStatus(role);
  if (!online) return;

  const images = role === 'learn' && learnImageBase64 ? [learnImageBase64] : [];
  const imageUrl = role === 'learn' ? learnImageDataUrl : null;
  const priorHistory = [...localHistories[role]];

  appendChatMessage(logElement, 'user', message, imageUrl);
  promptElement.value = '';
  buttonElement.disabled = true;

  try {
    const result = await postLocalAI(role, message, priorHistory, images);
    localHistories[role].push({role: 'user', content: message});
    localHistories[role].push({role: 'assistant', content: result.content});
    appendChatMessage(logElement, 'assistant', result.content);
  } catch (error) {
    appendChatMessage(logElement, 'assistant', `エラー: ${error.message}`);
  } finally {
    buttonElement.disabled = false;
    promptElement.focus();
  }
}

modeButton.addEventListener('click', (event) => {
  event.stopPropagation();
  const opening = modeMenu.classList.contains('hidden');
  modeMenu.classList.toggle('hidden', !opening);
  modeButton.setAttribute('aria-expanded', opening ? 'true' : 'false');
});

modeOptions.forEach((option) => {
  option.addEventListener('click', () => setMode(option.dataset.mode));
});

document.addEventListener('click', (event) => {
  if (!modeMenu.contains(event.target) && !modeButton.contains(event.target)) closeModeMenu();
});

toolButtons.forEach((button) => {
  button.addEventListener('click', () => showSidePanel(button.dataset.panel));
});

seedModeSelect.addEventListener('change', () => {
  seedValueInput.disabled = seedModeSelect.value !== 'FIXED';
});

promptInput.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (!generateButton.disabled) form.requestSubmit();
});

learnPrompt.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (!learnSend.disabled) learnForm.requestSubmit();
});

devPrompt.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (!devSend.disabled) devForm.requestSubmit();
});

learnImageInput.addEventListener('change', async () => {
  const file = learnImageInput.files?.[0];
  if (!file) return;

  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
    resetLearnImage();
    appendChatMessage(learnChatLog, 'assistant', 'PNG / JPEG / WebP の画像を選択してください。');
    return;
  }
  if (file.size > 20 * 1024 * 1024) {
    resetLearnImage();
    appendChatMessage(learnChatLog, 'assistant', '画像は20MB以下にしてください。');
    return;
  }

  try {
    const dataUrl = await readFileAsDataUrl(file);
    if (typeof dataUrl !== 'string' || !dataUrl.includes(',')) throw new Error('画像データ形式が不正です。');
    learnImageDataUrl = dataUrl;
    learnImageBase64 = dataUrl.split(',', 2)[1];
    learnImagePreview.src = dataUrl;
    learnImageWrap.hidden = false;
    learnImageRemove.hidden = false;
    learnImageName.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    learnUploadCopy.textContent = '画像を変更';
  } catch (error) {
    resetLearnImage();
    appendChatMessage(learnChatLog, 'assistant', `画像読込エラー: ${error.message}`);
  }
});

learnImageRemove.addEventListener('click', resetLearnImage);

learnForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  await handleLocalSubmit({role: 'learn', promptElement: learnPrompt, buttonElement: learnSend, logElement: learnChatLog});
});

devForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  await handleLocalSubmit({role: 'dev', promptElement: devPrompt, buttonElement: devSend, logElement: devChatLog});
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();

  let input;
  try {
    input = currentInput();
  } catch (error) {
    generationStatus.textContent = `エラー: ${error.message}`;
    generationStatus.classList.add('error');
    return;
  }

  generationStatus.textContent = '生成中...';
  generationStatus.classList.remove('error');
  generationMeta.textContent = '';
  generatedImage.hidden = true;
  imagePlaceholder.hidden = false;
  imagePlaceholder.textContent = '生成中...';
  generateButton.disabled = true;

  try {
    const payload = await postGenerate(input);
    jsonPreview.textContent = JSON.stringify(payload.request, null, 2);

    const generation = payload.generation;
    const inputMode = payload.request?.prompt_input?.mode || 'unknown';
    const generationMode = generation.generation_mode || payload.request?.target_mode || 'unknown';

    generatedImage.src = `${generation.output_url}?t=${Date.now()}`;
    generatedImage.hidden = false;
    imagePlaceholder.hidden = true;
    generationStatus.textContent = '生成完了';
    generationMeta.textContent = JSON.stringify({
      generation_id: generation.generation_id,
      input_mode: inputMode,
      generation_mode: generationMode,
      seed: generation.seed,
    }, null, 2);
  } catch (error) {
    generationStatus.textContent = `生成エラー: ${error.message}`;
    generationStatus.classList.add('error');
    imagePlaceholder.hidden = false;
    imagePlaceholder.textContent = '生成に失敗しました';
  } finally {
    generateButton.disabled = false;
  }
});

appendChatMessage(learnChatLog, 'assistant', '画像をアップロードして、何を確認したいか指示してください。解析結果は候補であり、dataset登録や学習は自動実行しません。');
appendChatMessage(devChatLog, 'assistant', 'GPTで作成したコード修正指示を貼り付けてください。現在は計画・解析のみで、ファイル変更は行いません。');
setMode('generate');

loadProfiles().catch((error) => {
  generationStatus.textContent = `Profile読込エラー: ${error.message}`;
  generationStatus.classList.add('error');
});
