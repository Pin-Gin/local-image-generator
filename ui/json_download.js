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

  async function acceptJsonPart(value, button) {
    const original = button.textContent;
    button.disabled = true;
    button.textContent = '検証・採用中...';
    try {
      const response = await fetch('/api/knowledge/json-part', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({document: value, accept: true}),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
      const result = payload.json_part;
      const preservation = result?.semantic_preservation === 'status-only';
      button.textContent = result?.oracle_indexed ? 'Part採用済み' : 'Part採用・保存済み';
      button.title = [
        `${result?.ref || 'JSON part'} をhash-gated staging→acceptedで採用しました`,
        preservation ? 'payload semantic preservation: OK' : 'payload semantic preservation: UNKNOWN',
        result?.payload_sha256 ? `payload SHA256: ${result.payload_sha256}` : null,
        result?.receipt_path ? `receipt: ${result.receipt_path}` : null,
        result?.oracle_indexed ? 'Oracle indexed' : 'Oracle not indexed',
      ].filter(Boolean).join('\n');
    } catch (error) {
      button.textContent = '採用失敗';
      button.title = error.message;
    } finally {
      window.setTimeout(() => {
        button.disabled = false;
        if (!button.textContent.includes('済み')) button.textContent = original;
      }, 2600);
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
      && value.status === 'staging'
    ) {
      const acceptButton = document.createElement('button');
      acceptButton.className = 'copy-message-button json-register-button';
      acceptButton.type = 'button';
      acceptButton.textContent = 'Part採用';
      acceptButton.title = '構造検証→staging固定→SHA256 gate→statusだけacceptedへ変更して採用';
      acceptButton.addEventListener('click', () => acceptJsonPart(value, acceptButton));
      roleRow.appendChild(acceptButton);
    }
  };
})();
