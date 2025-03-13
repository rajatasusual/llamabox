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

// Function to show a floating toast notification
function showToast(message) {
    let toast = document.createElement('div');
    toast.innerText = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.background = 'rgba(0, 0, 0, 0.8)';
    toast.style.color = 'white';
    toast.style.padding = '10px 15px';
    toast.style.borderRadius = '5px';
    toast.style.fontSize = '14px';
    toast.style.zIndex = '10000';
    toast.style.opacity = '1';
    toast.style.transition = 'opacity 0.5s ease-in-out';

    document.body.appendChild(toast);

    // Fade out and remove after 2 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => document.body.removeChild(toast), 500);
    }, 2000);
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

// Function to show a floating toast notification
function showToast(message) {
    let toast = document.createElement('div');
    toast.innerText = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.background = 'rgba(0, 0, 0, 0.8)';
    toast.style.color = 'white';
    toast.style.padding = '10px 15px';
    toast.style.borderRadius = '5px';
    toast.style.fontSize = '14px';
    toast.style.zIndex = '10000';
    toast.style.opacity = '1';
    toast.style.transition = 'opacity 0.5s ease-in-out';

    document.body.appendChild(toast);

    // Fade out and remove after 2 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => document.body.removeChild(toast), 500);
    }, 2000);
}
