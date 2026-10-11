(() => {
  const originalPostLocalAI = window.postLocalAI;
  if (typeof originalPostLocalAI !== 'function') return;

  window.postLocalAI = async function postLocalAIWithTools(role, message, history, images = []) {
    const toolRoles = new Set(['generate', 'learn', 'dev']);
    if (!toolRoles.has(role)) {
      return originalPostLocalAI(role, message, history, images);
    }

    const response = await fetch('/api/local-ai/tool-chat', {
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
  };
})();
