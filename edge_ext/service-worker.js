// Constants
const BADGE_COLORS = {
    ON: '#008000',
    OFF: '#CCCCC0'
};

// Badge Management
class BadgeManager {
    static async setState(state) {
        if (state === null) {
            state = await this.getState();
            if (state.enabled === undefined) {
                BadgeManager.setState(false);
            } else {
                BadgeManager.setState(state.enabled);
            }
            return;
        }
        await chrome.storage.sync.set({ enabled: state });
        console.log(`State set to: ${state}`);
        const badgeState = state ? "ON" : "OFF";
        await chrome.action.setBadgeText({ text: badgeState });
        await chrome.action.setBadgeBackgroundColor({
            color: BADGE_COLORS[badgeState]
        });
    }

    static async getState() {
        return await chrome.storage.sync.get("enabled");
    }
}

// API Service
class APIService {
    static async sendData(endpoint, data) {
        const result = await chrome.storage.sync.get("hostIp");
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
        const prevState = await BadgeManager.getState();
        const nextState = !prevState.enabled;

        await BadgeManager.setState(nextState);

        chrome.tabs.sendMessage(tabId, { toggleListener: nextState }, (response) => {
            if (chrome.runtime.lastError) {
                console.error("Error sending message:", chrome.runtime.lastError);
            }
        });
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

    static async updateTooltip() {
        const commands = await chrome.commands.getAll();
        const tooltipText = commands
            .filter(cmd => cmd.shortcut)
            .reduce((acc, cmd) =>
                acc + `${cmd.description}: ${cmd.shortcut}\n`,
                "Shortcuts:\n"
            );

        chrome.action.setTitle({ title: tooltipText });
    }
}


// Event Listeners
chrome.runtime.onInstalled.addListener(async () => {
    BadgeManager.setState(null);
    ExtensionController.updateTooltip();
    DataSyncManager.checkAlarmState();
});

chrome.commands.onCommand.addListener(async (command, tab) => {
    if (command === "toggle-extension") {
        ExtensionController.toggleExtension();
    } else if (command === "capture-page") {
        const state = await BadgeManager.getState();
        if (state.enabled) {
            ExtensionController.captureFullPage(tab);
        }
    }
});

chrome.action.onClicked.addListener((tab) => {
    ExtensionController.toggleExtension(tab.id);
});

chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === "sendStoredData") {
        DataSyncManager.sendStoredData();
    }
});
