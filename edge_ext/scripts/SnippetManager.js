class SnippetManager {
    constructor() {
        this.isListenerActive = false;
    }

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
        if (state && !this.isListenerActive) {
            document.addEventListener('mouseup', this.handleMouseUp, true);
            this.isListenerActive = true;
            console.log('Mouseup listener added.');
        } else if (!state && this.isListenerActive) {
            document.removeEventListener('mouseup', this.handleMouseUp, true);
            this.isListenerActive = false;
            console.log('Mouseup listener removed.');
        }
    }
}

const snippetManager = new SnippetManager();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.toggleListener) {
        snippetManager.toggleListener(message.toggleListener);
        sendResponse({ status: 'done' });
    } else if (!message.toggleListener) {
        snippetManager.toggleListener(false);
        sendResponse({ status: 'done' });
    }
});
