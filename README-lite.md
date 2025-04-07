# Llamabox <img src="assets/icon.png" width="16" height="16" style="vertical-align: middle"> Llamabox — Offline AI on a Low-End PC

**Self-host AI assistants, RAG pipelines, and knowledge graphs on WSL2.**  
**No GPU. No OpenAI keys. Just your CPU.**

[![Distro Health](https://github.com/rajatasusual/llamabox/actions/workflows/check.yml/badge.svg)](https://github.com/rajatasusual/llamabox/actions/workflows/check.yml)  
![WSL2](https://img.shields.io/badge/WSL2-Supported-blue) ![Debian](https://img.shields.io/badge/Debian-Supported-blue) ![License](https://img.shields.io/badge/License-MIT-green)

---

## ✅ What You Get

- **`llama.cpp`** → Fast CPU-only inference  
- **Redis Stack** → Store and search vector embeddings  
- **Neo4j** → Graph database for knowledge modeling  
- **Secure & resilient** → All services auto-managed with `systemd`  
- **Browser extension** → Capture web pages into your local knowledge base

⚡ Runs on: **4GB RAM**, **no GPU**, **offline**, **WSL2 Debian**

---

## 🖥️ Quick Start

```bash
# In Windows Terminal:
wsl --install -d Debian

# Then inside Debian:
sudo apt update && sudo apt install git -y
git clone https://github.com/rajatasusual/llamabox
cd llamabox
./setup.sh
```

📘 Full install guide: [INSTALLATION.md](docs/INSTALLATION.md)

---

## 🛠️ Basic Usage

```bash
# Check services
./scripts/check.sh

# Logs for AI server
sudo journalctl -u llama-server.service
```

📘 Manage services: [MANAGE.md](docs/MANAGE.md)

---

## 🧠 RAG Pipeline Flow

```
[User Query] → llama.cpp → Redis (vectors) → Neo4j (facts) → Response
```

All local. All CPU. No cloud needed.

---

## ❓ Common Fixes

> See full FAQ: [FAQs.md](docs/FAQs.md)

- 🔧 **Systemd not working?**  
  Add this to `/etc/wsl.conf`:
  ```ini
  [boot]
  systemd=true
  ```

- 🧠 **Model OOM crash?**  
  Try a smaller `.gguf` model or bump RAM via `.wslconfig`.

---

## 🔗 Links

- 📚 [Full Docs](docs/SUMMARY.md)  
- 🌐 [Browser Extension](https://github.com/rajatasusual/llamabox_extension)  
- 📈 [Benchmarks](#performance-benchmarks)

---

## 👥 Contribute

PRs welcome — fork → branch → PR  
Feature requests? Issues always appreciated.

---

## 📜 License

MIT. Built with ❤️ using:
- [llama.cpp](https://github.com/ggml-org/llama.cpp)  
- [Redis](https://redis.io)  
- [Neo4j](https://neo4j.com)  
- WSL2 (because Linux on Windows rocks)