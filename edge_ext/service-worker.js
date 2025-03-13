chrome.runtime.onInstalled.addListener(() => {
    chrome.action.setBadgeText({ text: "OFF" });
    chrome.action.setBadgeBackgroundColor({ color: '#CCCCC0' });

    // Set tooltip with shortcut information
    updateTooltip();
});

// Listen for shortcut commands
chrome.commands.onCommand.addListener(async (command, tab) => {

    if (command === "toggle-extension") {
        toggleExtension(tab);
    } else if (command === "capture-page") {
        const state = await chrome.action.getBadgeText({ tabId: tab.id });
        // Check if the extension is enabled
        if (state === 'OFF') {
            // If the extension is off, do nothing
            return;
        }
        captureFullPage(tab);
    }
});


chrome.action.onClicked.addListener(async (tab) => {
    toggleExtension(tab);
});

// Toggle the extension on/off
async function toggleExtension(tab) {
    // Retrieve the current badge text ('ON' or 'OFF')
    const prevState = await chrome.action.getBadgeText({ tabId: tab.id });
    // Determine the next state
    const nextState = prevState === 'ON' ? 'OFF' : 'ON';

    // Update the badge text and background color
    await chrome.action.setBadgeText({ tabId: tab.id, text: nextState });
    await chrome.action.setBadgeBackgroundColor({
        tabId: tab.id,
        color: nextState === 'ON' ? '#008000' : '#CCCCC0'
    });

    // Instead of injecting a script, send a message to the content script
    chrome.tabs.sendMessage(tab.id, { toggleListener: nextState }, (response) => {
        if (chrome.runtime.lastError) {
            console.error("Error sending message:", chrome.runtime.lastError);
        } else {
            console.log("Response from content script:", response);
        }
    });
}

// Capture entire page content
function captureFullPage(tab) {
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["scripts/readability.js", "scripts/capture-content.js"]
    });
}

async function updateTooltip() {
    const commands = await chrome.commands.getAll();
    let tooltipText = "Shortcuts:\n";

    commands.forEach(cmd => {
        if (cmd.shortcut === "") {
            return;
        }
        tooltipText += `${cmd.description}: ${cmd.shortcut || "Not set"}\n`;
    });

    chrome.action.setTitle({ title: tooltipText });
}