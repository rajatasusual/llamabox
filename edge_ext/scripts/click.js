let isListenerActive = false;

function handleMouseUp() {
    const selectedText = window.getSelection().toString();
    if (selectedText) {
        console.log('Selected text:', selectedText);

        const snippetData = {
            snippet: selectedText,
            url: window.location.href,
            title: document.title,
            date: new Date().toISOString()
        };

        chrome.storage.local.get('snippets', (result) => {
            let snippets = result.snippets || [];
            snippets.push(snippetData);
            chrome.storage.local.set({ snippets }, () => {
                console.log('Snippet saved:', snippetData);
                showToast("Snippet saved!");
            });
        });
    }
}

// Message listener to toggle the listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.toggleListener) {
        if (message.toggleListener === 'ON' && !isListenerActive) {
            document.addEventListener('mouseup', handleMouseUp, true);
            isListenerActive = true;
            console.log('Mouseup listener added.');
        } else if (message.toggleListener === 'OFF' && isListenerActive) {
            document.removeEventListener('mouseup', handleMouseUp, true);
            isListenerActive = false;
            console.log('Mouseup listener removed.');
        }
        sendResponse({ status: 'done' });
    }
});
