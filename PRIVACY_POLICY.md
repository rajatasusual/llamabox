# Privacy Policy

## Introduction

Welcome to the Llamabox project. This privacy policy outlines how we handle your data when you use our software, including the Llamabox application, [browser extension](https://github.com/rajatasusual/llamabox_extension), and associated services.

## Data Collection

### Local Data Storage

All data captured by the Llamabox, including snippets and full-page content, is stored locally on your machine. This includes:
- **Snippets:** Text selected and saved from webpages.
- **Full Page Content:** Main content extracted from articles using Mozilla's Readability.

### Local HTTP Server

The local HTTP server is offered to be used to sync captured pages and snippets from the [browser extension](https://github.com/rajatasusual/llamabox_extension). Data is stored in a folder named `data` with filenames in the format `{page/snippet}_timestamp.json`.

### Redis Queue (RQ)

We offer to use Redis Queue (RQ) for asynchronous task handling. This allows us to process workloads such as creating embeddings and storing them in Redis without blocking the main application.

## Data Processing

### Embeddings

Captured snippets are processed to create embeddings using the Llama-cpp server. These embeddings are then stored in Redis for efficient retrieval and search.

### Redis Storage

Processed data, including embeddings and metadata, is stored in Redis. This data is used to power the AI-powered RAG pipeline and other features of the Llamabox.

## Data Security

### Local Storage

All data is stored locally on your machine. We do not transmit your data to any external servers or third parties.

### Security Measures

We implement several security measures to protect your data:
- **Firewall (UFW) and Fail2Ban:** To prevent unauthorized access and brute-force attacks.
- **Automatic Security Updates:** To ensure the software remains secure against vulnerabilities.

## User Control

### Browser Extension

The [Llamabox browser extension](https://github.com/rajatasusual/llamabox_extension) allows you to capture and sync web content. You can configure the local server IP via the options page. Data synchronization is performed periodically using Chrome alarms.

### Data Deletion

You have full control over your data. You can delete captured snippets and full-page content from your local storage at any time.

## Changes to This Policy

We may update this privacy policy from time to time. Any changes will be posted on this page, and we will notify you of significant changes through the Llamabox application or browser extension.

## Contact Us

If you have any questions or concerns about this privacy policy, please contact us at [support@example.com].

---

**Effective Date:** [Insert Date]
