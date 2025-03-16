document.addEventListener("DOMContentLoaded", () => {
    const hostIpInput = document.getElementById("hostIp");
    const saveButton = document.getElementById("save");

    // Load saved host IP
    chrome.storage.sync.get("hostIp", (data) => {
        if (data.hostIp) {
            hostIpInput.value = data.hostIp;
        }
    });

    // Save host IP
    saveButton.addEventListener("click", () => {
        const hostIp = hostIpInput.value.trim();

        if (hostIp) {
            chrome.storage.sync.set({ hostIp }, () => {
                chrome.runtime.sendMessage({ hostIpChanged: true }, () => {
                    //send the service worker a message that the host IP has changed
                    showToast("Host IP saved! Autoclosing this window in 1 second.");
                    setTimeout(() => {//close the options page after 1 second
                        window.close();
                    }, 1000);
                });
            });


        } else {
            showToast("Please enter a valid host IP.");
        }
    });
});
