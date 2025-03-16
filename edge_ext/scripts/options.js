document.addEventListener("DOMContentLoaded", () => {
    const hostIpInput = document.getElementById("hostIp");
    const saveButton = document.getElementById("save");

    hostIpInput.addEventListener('input', () => {
        saveButton.disabled = !hostIpInput.checkValidity();
    });
    // Load saved host IP
    chrome.storage.sync.get("hostIp", (data) => {
        if (data.hostIp) {
            hostIpInput.value = data.hostIp;
        }
    });

    // Save host IP
    saveButton.addEventListener("click", () => {
        const hostIp = hostIpInput.value.trim();
        // Validate IP address format
        const ipRegex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        if (ipRegex.test(hostIp)) {
            // Check if the IP address is reachable
            showToast("Checking host IP...", "info");
            saveButton.innerHTML = '<span class="spinner"></span> Checking...';
            saveButton.disabled = true;
            fetch(`http://${hostIp}:5000/health`, { method: 'GET', mode: 'no-cors' })
                .then(response => {
                    if (response.ok) {
                        console.log("Host IP is reachable");
                        // Valid IP address
                        chrome.storage.sync.set({ hostIp }, () => {
                            chrome.runtime.sendMessage({ hostIpChanged: true }, () => {
                                saveButton.innerHTML = 'Save';
                                saveButton.disabled = false;
                                showToast("Host IP saved! Autoclosing this window in 1 second.", "info");
                                setTimeout(() => {
                                    window.close();
                                }, 1000);
                            });
                        });
                    } else {
                        console.error("Host IP is not reachable");
                        saveButton.innerHTML = 'Save';
                        saveButton.disabled = false;
                        showToast("Host IP is not reachable.", "error");
                        return;
                    }
                })
                .catch(error => {
                    console.error("Error checking host IP:", error);
                    saveButton.innerHTML = 'Save';
                    saveButton.disabled = false;
                    showToast("Error checking host IP.", "error");
                    return;
                });

        } else {
            // Invalid IP address
            showToast("Please enter a valid host IP.", "error");
            return;
        }
    });
});
