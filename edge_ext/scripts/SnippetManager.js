class SnippetManager {
    saveSnippet(snippetData) {
        chrome.storage.local.get('snippets', (result) => {
            let snippets = result.snippets || [];
            snippets.push(snippetData);
            chrome.storage.local.set({ snippets }, () => {
                console.log('Snippet saved:', snippetData);
                showToast("Snippet saved!");
            });
        });
    }

    createSnippetData(selectedText) {
        return {
            snippet: selectedText,
            url: window.location.href,
            title: document.title,
            date: new Date().toISOString()
        };
    }

    handleMouseUp = () => {
        const selectedText = window.getSelection().toString();
        if (selectedText) {
            console.log('Selected text:', selectedText);
            const snippetData = this.createSnippetData(selectedText);
            this.saveSnippet(snippetData);
        }
    }

    toggleListener(state) {
        if (state) {
            document.addEventListener('mouseup', this.handleMouseUp, true);
            console.log('Mouseup listener added.');
        } else if (!state) {
            document.removeEventListener('mouseup', this.handleMouseUp, true);
            console.log('Mouseup listener removed.');
        }
    }
}

const snippetManager = new SnippetManager();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.toggleListener !== undefined) {
        snippetManager.toggleListener(!!message.toggleListener);
        sendResponse({ status: 'done' });
    }
    if (message.refreshActive){
        snippetManager.toggleListener(message.refreshActive.state);
        sendResponse({ status: 'done' });
    }
    return true; // Keep the message channel open for sendResponse
});
