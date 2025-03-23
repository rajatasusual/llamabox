# Llamabox <img src="assets/icon.png" width="32" height="32" style="vertical-align: middle"> 

[![Distro Health](https://github.com/rajatasusual/llamabox/actions/workflows/check.yml/badge.svg?branch=master)](https://github.com/rajatasusual/llamabox/actions/workflows/check.yml) ![WSL2](https://img.shields.io/badge/WSL2-Supported-blue) ![Debian](https://img.shields.io/badge/Debian-Supported-blue) ![License](https://img.shields.io/badge/License-MIT-green)  

*Run a fully integrated AI and database stack on your low-end, CPU-only Windows machine—secure, resilient, and privacy-focused.*  

> **TL;DR:** Self-host AI on your low-end Windows PC using WSL2. Runs on CPU-only, needs just 1GB RAM. See [SUMMARY.md](docs/SUMMARY.md) for a quick overview.

Llamabox brings **on-device AI** to **low-power systems** by leveraging WSL2 and Debian. Unlike traditional AI setups that require **power-hungry GPUs**, this project is built **for CPUs only**—allowing you to run **efficient local inference** and a **full RAG pipeline** on even modest hardware.  

With Llamabox, you can **self-host AI assistants, chatbots, and knowledge graphs** without relying on external cloud APIs. The lightweight stack includes:  
✅ **llama.cpp** for blazing-fast **CPU inference**  
✅ **Redis Stack** for vector database storage  
✅ **Neo4j** for knowledge graphs  
✅ **Optimized for low-end Windows laptops & edge devices**  

With a memory footprint as low as **1GB**, Llamabox lets you run **local AI inference and an entire RAG pipeline on a 10-year-old device!**  

![WSL2](https://img.shields.io/badge/WSL2-Supported-blue)  ![Debian](https://img.shields.io/badge/Debian-Supported-blue)  ![License](https://img.shields.io/badge/License-MIT-green)  

![Memory](/assets/mem.png)  

---

## **1. Table of Contents**
- [1. Table of Contents](#1-table-of-contents)
- [2. Overview](#2-overview)
    - [2.1 Why This Project Exists?](#21-why-this-project-exists)
    - [2.2 Why WSL and Debian?](#22-why-wsl-and-debian)
    - [2.3 What Are the Components and Their Purpose?](#23-what-are-the-components-and-their-purpose)
- [3. Use Cases](#3-use-cases)
- [4. Features](#4-features)
    - [4.1 Security](#41-security)
    - [4.2 Resiliency](#42-resiliency)
    - [4.3 Privacy](#43-privacy)
    - [4.4 CPU-Optimized AI-Powered RAG Pipeline](#44-cpu-optimized-ai-powered-rag-pipeline)
- [5. Prerequisites](#5-prerequisites)
- [6. Installation](#6-installation)
- [7. Start the Services](#7-start-the-services)
- [8. Performance Benchmarks](#8-performance-benchmarks)
- [9. Roadmap](#9-roadmap)
- [10. Common Issues & Fixes](#10-common-issues--fixes)
- [11. Contributing](#11-contributing)
- [12. License](#12-license)
- [13. Credits](#13-credits)
- [14. Browser Extension](#14-browser-extension)

---

## **2. Overview**  

### **2.1 Why This Project Exists?**  
Most AI frameworks are built for **high-end GPUs**, making them **unusable on older machines** or **low-power edge devices**. Llamabox solves this by providing:  
- **A fully integrated CPU-based AI environment** for local inference.  
- **A lightweight stack (only ~1GB RAM)** to run AI models without lag.  
- **An optimized RAG pipeline** with Redis + Neo4j for AI-powered retrieval.  
- **No cloud dependency**—your data stays **local and private**.  

### **2.2 Why WSL and Debian?**  
- **WSL2**: Runs Linux on Windows with near-native performance.  
- **Debian**: Stable, secure, and lightweight—ideal for low-resource machines.  
- **No need for Docker**: Avoids container overhead while still maintaining isolation.  

### **2.3 What Are the Components and Their Purpose?**  
| Component      | Purpose |
|---------------|---------|
| **Redis Stack**  | Fast vector database for AI embeddings |
| **Neo4j**       | Graph database for knowledge management |
| **llama.cpp**   | Local AI inference engine (CPU-optimized) |
| **Fail2Ban & UFW** | Security hardening against brute-force attacks |
| **Systemd Auto-Restart** | Ensures services are resilient to crashes |
| **Local HTTP Server** | Syncs captured pages/snippets from the [browser extension](https://github.com/rajatasusual/llamabox_extension) |
| **Redis Queue (RQ)** | Asynchronous task handling for creating embeddings and storing them in Redis |

---

## **3. Use Cases**  
- **AI-powered local search**: Store and retrieve knowledge with Redis + Neo4j.  
- **Self-hosted AI assistant**: Use `llama.cpp` for **CPU-only inference**.  
- **Privacy-first chatbots**: Avoid OpenAI/Google APIs—run everything **offline**.  
- **Edge AI applications**: Ideal for **low-end devices** with limited compute.  
- **Web Content Capture**: Use the [browser extension](https://github.com/rajatasusual/llamabox_extension) to capture and sync web content.

---

## **4. Features**  

### **4.1 Security** 🔒  
✅ **Disables root SSH login**  
✅ **Enables firewall (ufw) and Fail2Ban** to prevent attacks  
✅ **Automatic security updates**  

### **4.2 Resiliency** 🔄  
✅ **Auto-restarts essential services** after crashes  
✅ **Persistent Redis storage** for AI embeddings  
✅ **WSL2 optimizations for memory efficiency**  

### **4.3 Privacy** 🛡️  
✅ No external cloud dependencies  
✅ Local **AI inference with llama.cpp**  
✅ **Fully air-gapped if needed**  

### **4.4 CPU-Optimized AI-Powered RAG Pipeline** 🤖  
1️⃣ **User query →** Sent to `llama.cpp` (CPU-only)  
2️⃣ **Query transformed →** Passed to Redis vector DB  
3️⃣ **Relevant knowledge retrieved →** From Neo4j knowledge graph  
4️⃣ **Final AI response →** AI generates response  

---

## **5. Prerequisites**  
- **Windows 10/11 with WSL2** enabled  
- **At least 4GB RAM** (8GB recommended for AI inference with >1b parameter models)  
- **At least 20GB free disk space**  

---

## **6. Installation**  

```bash
# Install WSL2 and Debian
wsl --install -d Debian

# Clone this repo
git clone https://github.com/rajatasusual/llamabox.git
cd llamabox

# Run setup script
./setup.sh
```

For **detailed setup instructions**, see [INSTALLATION.md](docs/INSTALLATION.md).  
For **frequently seen issues**, see [FAQs.md](docs/FAQs.md).

---

## **7. Start the Services**  

```bash
# Start all required services
./start.sh
```

For troubleshooting, see logs in `/var/log/llamabox/`.

---

## **8. Performance Benchmarks**  

Llamabox is optimized for **low-latency CPU-only inference**. Below is a benchmark of `llama 3B Q8_0` on a low-end WSL2 setup.  

### **Test System Specs:**  
📌 **RAM:** 4GB  
📌 **Storage:** 20GB  
📌 **Processor:** AMD Z1 Extreme  
📌 **# Cores:** 4  
📌 **GPU:** ❌ (None—CPU-only inference)  
📌 **OS:** Debian (WSL2)  

### **Tokens Per Second (T/s) Benchmarks:**  

| Model            | Size      | Params    | Backend | Threads | Test Type | Tokens/sec (± std) |
|-----------------|----------:|----------:|---------|--------:|----------:|-------------------:|
| **LLaMA 3B Q8_0** | 366.8MB  | 361.82M  | CPU     | 2       | pp512     | 253.07 ± 23.75    |
| **LLaMA 3B Q8_0** | 366.8MB  | 361.82M  | CPU     | 2       | tg128     | 54.44 ± 4.87      |

![Tokens per second](assets/tpt.png)

### **Interpreting These Results**  
✅ **Blazing fast inference on just a CPU!**  
✅ **Low power consumption—runs smoothly on a 4GB RAM system!**  
✅ **Ideal for low-end edge devices & offline AI assistants!**  

---

## **9. Roadmap**  
Please see [TODO.md](TODO.md) for our detailed roadmap. This project is under active development, and we welcome community input on prioritizing features.

---

## **10. Common Issues & Fixes**  

❓ **Q: Redis Stack Server is not starting**  
✅ **Fix**: Run `sudo systemctl restart redis-stack-server`  

❓ **Q: "Out of memory" error when loading models**  
✅ **Fix**:  
- Try a smaller GGUF model (`SmolLM2-360M-Instruct.q8.gguf`)  
- Increase **WSL2 memory**: Edit `.wslconfig` and set:  
  ```ini
  [wsl2]
  memory=8GB
  ```

---

## **11. Contributing**  
Contributions are welcome!  

1. Fork the repository  
2. Create a new branch (`feature-xyz`)  
3. Submit a **pull request**  

---

## **12. License**  
This project is licensed under the **MIT License**.  

---

## **13. Credits**  
Shout-out to:  
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** for CPU-based AI inference  
- **[Redis](https://redis.io/)** for vector storage  
- **[Neo4j](https://neo4j.com/)** for knowledge graphs  
- **The WSL Community** for making Linux on Windows seamless  

---

## **14. Browser Extension**

Llamabox can be used with a lightweight [browser extension](https://github.com/rajatasusual/llamabox_extension) to capture web content for your AI-powered knowledge base:

✅ **Quick Content Capture**:
- Select text snippets from any webpage
- Extract full article content using Mozilla's Readability
- Keyboard shortcuts for quick actions (Ctrl+B, Alt+B)

✅ **Key Features**:
- Automatic sync with local WSL server
- Secure data storage and transmission
- Easy configuration via options page
- Dynamic status indicators
- Works offline with periodic sync

✅ **Installation**:
Load as an unpacked extension in Chrome/Edge and configure your WSL host IP.

For detailed setup instructions and documentation, see [README.md](https://github.com/rajatasusual/llamabox_extension/blob/master/README.md).
