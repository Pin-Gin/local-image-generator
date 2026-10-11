(() => {
  function getClipboardImage(event) {
    const items = [...(event.clipboardData?.items || [])];
    for (const item of items) {
      if (item.kind !== 'file' || !item.type.startsWith('image/')) continue;
      const file = item.getAsFile();
      if (file) return file;
    }
    return null;
  }

  document.addEventListener('paste', async (event) => {
    const learnView = document.getElementById('learn-view');
    if (!learnView || learnView.classList.contains('hidden')) return;

    const image = getClipboardImage(event);
    if (!image) return;

    event.preventDefault();

    try {
      await loadLearnImageFile(image);
    } catch (error) {
      appendChatMessage(
        document.getElementById('learn-chat-log'),
        'assistant',
        `スクリーンショット貼り付けエラー: ${error.message}`,
      );
    }
  });
})();
