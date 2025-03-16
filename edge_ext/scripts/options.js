document.addEventListener("DOMContentLoaded", () => {
    const hostIpInput = document.getElementById("hostIp");
    const saveButton = document.getElementById("save");
    const statusText = document.getElementById("status");

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
                statusText.textContent = "Host IP saved successfully!";
                setTimeout(() => (statusText.textContent = ""), 3000);
            });
        } else {
            statusText.textContent = "Please enter a valid IP address.";
        }
    });
});
