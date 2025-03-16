// Constants
const BADGE_COLORS = {
    ON: '#008000',
    OFF: '#CCCCC0',
    WARN: '#FFA500'
};

class BadgeManager {
    static async updateBadge() {

        const setBadge = async (text, color) => {
            await chrome.action.setBadgeText({ text });
            await chrome.action.setBadgeBackgroundColor({ color });
        };

        const state = await StatusManager.getState();
        const ipConfig = await StatusManager.getHostIp();

        if (!ipConfig.hostIp) {
            await setBadge("!", BADGE_COLORS.WARN);
            ExtensionController.updateTooltip("Host IP not set.");
            return;
        }

        await setBadge(
            state.enabled ? "ON" : "OFF",
            state.enabled ? BADGE_COLORS.ON : BADGE_COLORS.OFF
        );
    }
}

// Status Management
class StatusManager {
    static async setState(state) {
        if (state === null) {
            state = await this.getState();
            if (state.enabled === undefined) {
                StatusManager.setState(false);
            } else {
                StatusManager.setState(state.enabled);
            }
            return;
        }
        await chrome.storage.sync.set({ enabled: state });
        BadgeManager.updateBadge();

        console.log(`State set to: ${state}`);
    }

    static async getState() {
        return await chrome.storage.sync.get("enabled");
    }

    static async getHostIp() {
        const result = await chrome.storage.sync.get("hostIp");
        return result;
    }
}

// API Service
class APIService {
    static async sendData(endpoint, data) {
        const result = await StatusManager.getHostIp();
        if (!result.hostIp) {
            console.warn("Host IP is not set. Skipping data upload.");
            return false;
        }

        const API_BASE_URL = `http://${result.hostIp}:5000`;
        console.log(`Sending data to ${API_BASE_URL}/${endpoint}`);
        try {
            const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                console.log(`${endpoint} successfully sent.`);
                return true;
            }
            console.error(`Failed to send ${endpoint}.`);
            return false;
        } catch (error) {
            console.error(`Error sending ${endpoint}:`, error);
            return false;
        }

    }
}

// Data Sync Manager
class DataSyncManager {
    static async sendStoredData() {
        const { snippets = [], capturedPages = [] } = await chrome.storage.local.get([
            "snippets",
            "capturedPages"
        ]);

        if (snippets.length > 0) {
            const success = await APIService.sendData('snippet', snippets);
            if (success) await chrome.storage.local.set({ snippets: [] });
            else
                console.warn("Failed to send snippets. Retaining in storage.");
        }

        if (capturedPages.length > 0) {
            const success = await APIService.sendData('page', capturedPages);
            if (success) await chrome.storage.local.set({ capturedPages: [] });
            else
                console.warn("Failed to send captured pages. Retaining in storage.");
        }
    }

    static async checkAlarmState() {
        const alarm = await chrome.alarms.get("sendStoredData");
        if (!alarm) {
            await chrome.alarms.create("sendStoredData", { periodInMinutes: 1 });
        }
    }
}

// Extension Controller
class ExtensionController {
    static async toggleExtension(tabId) {
        const prevState = await StatusManager.getState();
        const nextState = !prevState.enabled;

        await StatusManager.setState(nextState);

       await this.updateAllTabs();
    }

    static captureFullPage(tab) {
        chrome.tabs.sendMessage(tab.id, { action: "capturePage" }, (response) => {
            if (chrome.runtime.lastError) {
                console.error("Error sending message:", chrome.runtime.lastError);
            } else {
                console.log("Capture page response:", response);
            }
        });
    }

    static async updateTooltip(message) {
        if (message) {
            chrome.action.setTitle({ title: message });
            return;
        }
        const commands = await chrome.commands.getAll();
        const tooltipText = commands
            .filter(cmd => cmd.shortcut)
            .reduce((acc, cmd) =>
                acc + `${cmd.description}: ${cmd.shortcut}\n`,
                "Shortcuts:\n"
            );

        chrome.action.setTitle({ title: tooltipText });
    }

    static async reinjectContentScript() {
        for (const cs of chrome.runtime.getManifest().content_scripts) {
            for (const tab of await chrome.tabs.query({ url: cs.matches })) {
                if (tab.url.match(/(chrome|chrome-extension|edge|extension):\/\//gi)) {
                    continue;
                }
                const target = { tabId: tab.id, allFrames: cs.all_frames };
                if (cs.js[0]) chrome.scripting.executeScript({
                    files: cs.js,
                    injectImmediately: cs.run_at === 'document_start',
                    world: cs.world, // requires Chrome 111+
                    target,
                });
            }
        }
    }
    static async updateAllTabs() {
        for (const tab of await chrome.tabs.query({ url: "<all_urls>" })) {
            if (tab.url.match(/(chrome|chrome-extension|edge|extension):\/\//gi)) {
                continue;
            }
            const state = await StatusManager.getState();
            chrome.tabs.sendMessage(tab.id, { refreshActive: { state } }, (response) => {
                if (chrome.runtime.lastError) {
                    // This error indicates that the content script isn't present in the tab.
                    console.warn(`Tab ${tab.id} did not receive the message: ${chrome.runtime.lastError.message}`);
                } else {
                    console.log(`Tab ${tab.id} updated successfully.`);
                }
            });
        }
    }
}


// Event Listeners
chrome.runtime.onInstalled.addListener(async () => {
    StatusManager.setState(null);
    ExtensionController.updateTooltip();
    DataSyncManager.checkAlarmState();
    ExtensionController.reinjectContentScript();
    
    chrome.runtime.openOptionsPage();

    console.log("Extension installed.");
});

chrome.commands.onCommand.addListener(async (command, tab) => {
    if (command === "toggle-extension") {
        ExtensionController.toggleExtension();
    } else if (command === "capture-page") {
        const state = await StatusManager.getState();
        if (state.enabled) {
            ExtensionController.captureFullPage(tab);
        }
    }
});

chrome.action.onClicked.addListener(async (tab) => {
    const hostIp = await StatusManager.getHostIp();
    //open options page if hostIp is not set
    if (!hostIp.hostIp) {
        chrome.runtime.openOptionsPage();
        return;
    }
    ExtensionController.toggleExtension(tab.id);
});

chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === "sendStoredData") {
        DataSyncManager.sendStoredData();
    }
});

//listen to host IP changes
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.hostIpChanged) {
        StatusManager.getHostIp().then(async (hostIp) => {
            // Also update the badge if necessary.
            BadgeManager.updateBadge();

            // Send a response if needed.
            sendResponse({ status: "Host IP updated across all tabs." });
        });
        // Return true to indicate asynchronous response.
        return true;
    }
});
