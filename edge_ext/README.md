# WSL Extension

## Overview

WSL Extension is a lightweight browser extension designed to help you capture valuable web content quickly and efficiently. Whether you need to save a selected snippet or extract the main article content from a page using Mozilla's Readability, WSL Extension streamlines the process with a simple click or keyboard shortcut.

## Use Case

Modern web browsing is filled with information you might want to save for research, writing, or personal reference. With WSL Extension, you can capture:
- **Snippets:** Save selected text from any webpage.
- **Full Page Content:** Extract the primary content from an article.
- **Automatic Data Sync:** Periodically send your captured content to a local server for backup or further processing.

This tool is especially useful for researchers, writers, or anyone who needs to organize and save content without interrupting their browsing experience.

## Features

- **Capture Snippets:** Instantly save selected text.
- **Full Page Capture:** Leverage Mozilla's Readability to extract and save the main content of a webpage.
- **Keyboard Shortcuts:**
  - **Ctrl+B:** Toggle the extension on or off.
  - **Alt+B:** Capture full page content.
- **Options Page for Host Configuration:** Configure the WSL server IP for data uploads.
- **Automatic Data Synchronization:** Uses chrome alarms to periodically send stored data to your configured local server.
- **Dynamic Badge & Tooltip:** Provides real-time visual feedback on the extension status and any configuration issues.
- **Security Focused:** Implements strict Content Security Policies (CSP) and sanitizes inputs to minimize risks.
- **Lightweight & Fast:** Designed to run unobtrusively in the background without impacting your browsing performance.

## Security

WSL Extension prioritizes your safety by incorporating several security measures:
- **Content Security Policy (CSP):** Limits the sources for scripts and assets to reduce exposure to malicious content.
- **Input Sanitization:** Cleans user-selected content to prevent the storage or execution of harmful scripts.
- **User Configurable Server:** By allowing you to set the host IP via the options page, the extension avoids hardcoding sensitive network details.

## Installation

1. **Clone or Download:** Obtain the extension's source code from the repository.
2. **Load the Extension:**
   - Open your browser's extension management page (e.g., `chrome://extensions` or `edge://extensions`).
   - Enable Developer Mode.
   - Click on "Load unpacked" and select the extension folder.
3. **Configure Host IP:** On installation, the extension automatically opens the options page. Enter your local WSL server IP here.
4. **Start Capturing:** Once configured, use the extension icon or the keyboard shortcuts to capture content.

## Usage

- **Toggle Extension:** Click the extension icon or press **Ctrl+B** to enable/disable the extension.
- **Capture Snippets:** When enabled, simply highlight text on any webpage to capture a snippet.
- **Capture Full Page Content:** Press **Alt+B** to extract and save the main content of the current page.
- **Data Synchronization:** Captured data is stored locally and periodically sent to your configured endpoints:
  - **Snippets Endpoint:** `http://<host-ip>:5000/snippet`
  - **Page Content Endpoint:** `http://<host-ip>:5000/page`

## Options & Configuration

- **Host IP Configuration:** Use the options page to set the IP address of your local WSL server. This value is stored using `chrome.storage.sync` and is used by the extension for data uploads.
- **Dynamic Updates:** When you change the host IP in the options page, the extension broadcasts the update to all open tabs and refreshes the badge status accordingly.

## Data Synchronization

WSL Extension periodically synchronizes stored data with your local server:
- **Local Storage:** Captured snippets and full-page content are stored using `chrome.storage.local`.
- **Periodic Sync:** The extension uses chrome alarms to trigger data uploads every minute.
- **API Endpoints:**
  - **Snippet Upload:** Sends an array of snippets to `http://<host-ip>:5000/snippet`.
  - **Page Content Upload:** Sends an array of captured pages to `http://<host-ip>:5000/page`.

## Troubleshooting

- **Host IP Not Set:** If the extension badge displays an exclamation mark ("!") and the tooltip indicates "Host IP not set," configure the host IP via the options page.
- **Content Script Not Injected:** Some pages (e.g., chrome internal pages) may not allow content script injection. These errors are logged and do not impact overall functionality.
- **Connection Issues:** Ensure your local server is running and accessible at the specified IP and port.
- **Message Errors:** If you encounter "Receiving end does not exist" errors, it may be because a particular tab doesn’t have the content script injected. The extension logs these occurrences without affecting overall performance.