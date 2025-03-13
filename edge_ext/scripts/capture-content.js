function captureReadableContent() {
    try {
        const article = new Readability(document.cloneNode(true)).parse();
        if (article) {
            const pageData = {
                title: article.title || document.title,
                content: article.textContent,
                url: window.location.href,
                date: new Date().toISOString()
            };

            chrome.storage.local.get('capturedPages', (result) => {
                let pages = result.capturedPages || [];
                pages.push(pageData);
                chrome.storage.local.set({ capturedPages: pages }, () => {
                    console.log('Page content saved:', pageData);
                    showToast("Page content captured!");
                });
            });
        } else {
            console.log("No readable content found.");
            showToast("No readable content detected.");
        }
    } catch (error) {
        console.error("Error capturing content:", error);
        showToast("Error capturing content.");
    }
}

captureReadableContent();