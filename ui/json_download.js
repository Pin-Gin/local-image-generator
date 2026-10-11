(() => {
  const originalAppend = window.appendChatMessage;
  if (typeof originalAppend !== 'function') return;

  function extractJson(text) {
    const trimmed = String(text || '').trim();
    const candidates = [trimmed];
    const fencePattern = /```(?:json)?\s*([\s\S]*?)```/gi;
    let match;
    while ((match = fencePattern.exec(trimmed)) !== null) {
      candidates.push(match[1].trim());
    }
    const startObject = trimmed.indexOf('{');
    const endObject = trimmed.lastIndexOf('}');
    if (startObject >= 0 && endObject > startObject) {
      candidates.push(trimmed.slice(startObject, endObject + 1));
    }
    const startArray = trimmed.indexOf('[');
    const endArray = trimmed.lastIndexOf(']');
    if (startArray >= 0 && endArray > startArray) {
      candidates.push(trimmed.slice(startArray, endArray + 1));
    }

    for (const candidate of candidates) {
      try {
        const value = JSON.parse(candidate);
        if (value !== null && typeof value === 'object') return value;
      } catch (_) {
        // Try the next candidate.
      }
    }
    return null;
  }

  function safeFilename(value) {
    return String(value || 'local-rag-ai')
      .replace(/[^a-zA-Z0-9._-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 80) || 'local-rag-ai';
  }

  function downloadJson(value) {
    const pretty = JSON.stringify(value, null, 2) + '\n';
    const blob = new Blob([pretty], {type: 'application/json;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    const base = value?.part_id
      ? `${value.part_id}.v${value.version || 1}`
      : value?.id || value?.name || 'local-rag-ai-response';
    anchor.href = url;
    anchor.download = `${safeFilename(base)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function registerJsonPart(value, button, {accept = false} = {}) {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = accept ? '採用中...' : '登録中...';
    try {
      const document = accept ? {...value, status: 'accepted'} : value;
      const response = await fetch('/api/knowledge/json-part', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({document}),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      const result = payload.json_part;
      if (accept) {
        button.textContent = result?.oracle_indexed ? 'Part採用済み' : 'Part採用・保存済み';
        button.title = result?.oracle_indexed
          ? `${result.ref} をacceptedとして保存しOracleへ索引登録しました`
          : `${result?.ref || 'JSON part'} をacceptedとして保存しました。Oracleは未索引です`;
      } else {
        button.textContent = result?.oracle_indexed ? 'Part登録済み' : 'Part保存済み';
        button.title = result?.oracle_indexed
          ? `${result.ref} をファイル保存しOracleへ索引登録しました`
          : `${result?.ref || 'JSON part'} をファイル保存しました。Oracleは未索引です`;
      }
    } catch (error) {
      button.textContent = accept ? '採用失敗' : '登録失敗';
      button.title = error.message;
    } finally {
      window.setTimeout(() => {
        button.disabled = false;
        if (!button.textContent.includes('済み')) button.textContent = original;
      }, 2200);
    }
  }

  window.appendChatMessage = function appendChatMessageWithJsonDownload(container, role, text, imageUrl = null) {
    originalAppend(container, role, text, imageUrl);
    if (role !== 'assistant') return;

    const value = extractJson(text);
    if (value === null) return;

    const item = container.lastElementChild;
    const roleRow = item?.querySelector('.chat-role-row');
    if (!roleRow) return;

    const button = document.createElement('button');
    button.className = 'copy-message-button json-download-button';
    button.type = 'button';
    button.textContent = 'JSON保存';
    button.title = 'JSONをファイルとして保存';
    button.addEventListener('click', () => downloadJson(value));
    roleRow.appendChild(button);

    if (
      !Array.isArray(value)
      && value.document_type === 'local-rag/json-part'
      && typeof value.part_id === 'string'
      && Number.isInteger(value.version)
    ) {
      const registerButton = document.createElement('button');
      registerButton.className = 'copy-message-button json-register-button';
      registerButton.type = 'button';

      if (value.status === 'staging') {
        registerButton.textContent = 'Part採用';
        registerButton.title = 'この候補を明示的に採用し、acceptedとして永続ストアとOracleへ登録';
        registerButton.addEventListener('click', () => registerJsonPart(value, registerButton, {accept: true}));
      } else {
        registerButton.textContent = 'Part登録';
        registerButton.title = 'このJSON Partをlocal-RAGの永続ストアへ登録';
        registerButton.addEventListener('click', () => registerJsonPart(value, registerButton));
      }

      roleRow.appendChild(registerButton);
    }
  };
})();
