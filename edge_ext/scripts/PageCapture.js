class PageCapture {
    createPageData(article) {
        return {
            title: article.title || document.title,
            content: article.textContent,
            url: window.location.href,
            date: new Date().toISOString()
        };
    }

    async saveToStorage(pageData) {
        return new Promise((resolve, reject) => {
            chrome.storage.local.get('capturedPages', (result) => {
                const pages = result.capturedPages || [];
                pages.push(pageData);
                chrome.storage.local.set({ capturedPages: pages }, () => {
                    if (chrome.runtime.lastError) {
                        reject(chrome.runtime.lastError);
                        return;
                    }
                    resolve();
                });
            });
        });
    }

    async captureReadableContent() {
        try {
            const article = new Readability(document.cloneNode(true)).parse();
            if (!article) {
                console.log("No readable content found.");
                showToast("No readable content detected.");
                return;
            }

            const pageData = this.createPageData(article);
            await this.saveToStorage(pageData);
            
            console.log('Page content saved:', pageData);
            showToast("Page content captured!");

        } catch (error) {
            console.error("Error capturing content:", error);
            showToast("Error capturing content.");
        }
    }
}

const pageCapture = new PageCapture();


chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "capturePage") {
        pageCapture.captureReadableContent();
        sendResponse({ status: 'done' });
    }
    return true; // Keep the message channel open for sendResponse
});