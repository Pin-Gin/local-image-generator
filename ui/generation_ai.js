(() => {
  const status = document.getElementById('generate-ai-status');
  const autoToggle = document.getElementById('generate-ai-auto');
  const sendToLearnButton = document.getElementById('send-generated-to-learn');
  const chatLog = document.getElementById('generate-ai-chat-log');
  const aiForm = document.getElementById('generate-ai-form');
  const aiPrompt = document.getElementById('generate-ai-prompt');
  const aiSend = document.getElementById('generate-ai-send');

  if (!status || !autoToggle || !sendToLearnButton || !chatLog || !aiForm || !aiPrompt || !aiSend) {
    return;
  }

  if (!Array.isArray(localHistories.generate)) localHistories.generate = [];

  let currentImageBase64 = null;
  let currentImageDataUrl = null;
  let currentImageBlob = null;
  let lastGenerationPrompt = '';
  let lastCapturedSrc = '';
  let autoAnalysisInFlight = false;

  async function loadGenerateAIStatus() {
    status.textContent = '確認中...';
    status.className = 'status-pill';

    try {
      const response = await fetch('/api/local-ai/status', {cache: 'no-store'});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);

      const roleInfo = payload.local_ai?.roles?.generate;
      if (!roleInfo) throw new Error('generate role unavailable');
      if (!roleInfo.installed) {
        status.textContent = `モデル未導入: ${roleInfo.model}`;
        status.classList.add('warning');
        return false;
      }

      status.textContent = `オンライン: ${roleInfo.model}`;
      status.classList.add('online');
      return true;
    } catch (error) {
      status.textContent = `オフライン: ${error.message}`;
      status.classList.add('error');
      return false;
    }
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error || new Error('生成画像を読み込めませんでした。'));
      reader.readAsDataURL(blob);
    });
  }

  async function captureGeneratedImage() {
    const src = generatedImage.getAttribute('src');
    if (!src || generatedImage.hidden) return false;
    if (src === lastCapturedSrc && currentImageBase64) return true;

    const response = await fetch(src, {cache: 'no-store'});
    if (!response.ok) throw new Error(`生成画像 HTTP ${response.status}`);
    const blob = await response.blob();
    const dataUrl = await blobToDataUrl(blob);
    if (typeof dataUrl !== 'string' || !dataUrl.includes(',')) {
      throw new Error('生成画像のデータ形式が不正です。');
    }

    currentImageBlob = blob;
    currentImageDataUrl = dataUrl;
    currentImageBase64 = dataUrl.split(',', 2)[1];
    lastCapturedSrc = src;
    sendToLearnButton.disabled = false;
    return true;
  }

  function buildGenerationContext(message) {
    const prompt = lastGenerationPrompt || promptInput.value.trim();
    if (!prompt) return message;
    return `元の生成指示:\n${prompt}\n\nユーザーの確認内容:\n${message}`;
  }

  async function sendGenerateAI(message, {automatic = false} = {}) {
    const online = await loadGenerateAIStatus();
    if (!online) return;

    try {
      await captureGeneratedImage();
    } catch (error) {
      appendChatMessage(chatLog, 'assistant', `生成画像読込エラー: ${error.message}`);
      return;
    }

    const images = currentImageBase64 ? [currentImageBase64] : [];
    const priorHistory = [...localHistories.generate];
    const requestMessage = buildGenerationContext(message);

    if (!automatic) appendChatMessage(chatLog, 'user', message, currentImageDataUrl);
    aiSend.disabled = true;

    try {
      const result = await postLocalAI('generate', requestMessage, priorHistory, images);
      localHistories.generate.push({role: 'user', content: requestMessage});
      localHistories.generate.push({role: 'assistant', content: result.content});
      appendChatMessage(chatLog, 'assistant', result.content);
    } catch (error) {
      appendChatMessage(chatLog, 'assistant', `エラー: ${error.message}`);
    } finally {
      aiSend.disabled = false;
      if (!automatic) aiPrompt.focus();
    }
  }

  async function runAutoAnalysis() {
    if (!autoToggle.checked || autoAnalysisInFlight) return;
    autoAnalysisInFlight = true;
    appendChatMessage(chatLog, 'assistant', '生成画像を自動解析しています...');
    try {
      await sendGenerateAI(
        '生成指示と生成結果を比較してください。特にポーズ、左右の腕と手、見えている指、表情、衣装、背景、カメラ構図、レンダリングを分けて確認し、不明瞭な箇所は推測せず明記してください。学習候補があれば候補として示してください。ただしdataset登録や学習実行はしないでください。',
        {automatic: true},
      );
    } finally {
      autoAnalysisInFlight = false;
    }
  }

  form.addEventListener('submit', () => {
    lastGenerationPrompt = promptInput.value.trim();
    currentImageBase64 = null;
    currentImageDataUrl = null;
    currentImageBlob = null;
    lastCapturedSrc = '';
    sendToLearnButton.disabled = true;
  });

  const observer = new MutationObserver(async () => {
    if (generatedImage.hidden || !generatedImage.getAttribute('src')) return;
    try {
      const captured = await captureGeneratedImage();
      if (captured) await runAutoAnalysis();
    } catch (error) {
      appendChatMessage(chatLog, 'assistant', `生成画像読込エラー: ${error.message}`);
    }
  });
  observer.observe(generatedImage, {attributes: true, attributeFilter: ['src', 'hidden']});

  aiForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = aiPrompt.value.trim();
    if (!message) return;
    aiPrompt.value = '';
    await sendGenerateAI(message);
  });

  aiPrompt.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    if (!aiSend.disabled) aiForm.requestSubmit();
  });

  sendToLearnButton.addEventListener('click', async () => {
    try {
      if (!currentImageBlob) await captureGeneratedImage();
      if (!currentImageBlob) throw new Error('学習へ送れる生成画像がありません。');

      const type = currentImageBlob.type || 'image/png';
      const extension = type.includes('jpeg') ? 'jpg' : type.includes('webp') ? 'webp' : 'png';
      const file = new File([currentImageBlob], `generated-${Date.now()}.${extension}`, {type});
      await loadLearnImageFile(file);
      setMode('learn');
      appendChatMessage(
        learnChatLog,
        'assistant',
        '直前の生成画像を学習モードへ読み込みました。何を学習対象として検討するか指示してください。まだdataset登録や学習実行はしていません。',
      );
    } catch (error) {
      appendChatMessage(chatLog, 'assistant', `学習モードへの転送エラー: ${error.message}`);
    }
  });

  appendChatMessage(
    chatLog,
    'assistant',
    '生成結果についてローカルAIと会話できます。生成画像がある場合は、その画像と元の生成指示を一緒に確認します。',
  );
  loadGenerateAIStatus();
})();
