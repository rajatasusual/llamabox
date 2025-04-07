### **Llamabox - Setup Summary**  

This is a **high-level overview** of your full setup—spanning installation, AI services, database integrations, security, and performance optimization.  

For command-line references, see [MANAGE.md](/docs/MANAGE.md).

---

## 🛠 1. System Setup (WSL & Debian)  
✅ Install **WSL2** and **Debian** on Windows  
✅ Allocate **at least 4GB RAM & 20GB storage**  
✅ Clone the repo and run the auto-installer  

```bash
wsl --install -d Debian
git clone https://github.com/rajatasusual/llamabox.git
cd llamabox
./setup.sh
```

> 💡 For WSL2 IP, memory, and shutdown commands, see `MANAGE.md > PowerShell`.

---

## 📦 2. Database & Vector Store  

### 🔴 **Redis Stack (Vector Embeddings)**  
✅ Installed and configured **Redis Stack**  
✅ Enabled **persistence** to avoid data loss  
✅ Auto-start on boot with `systemctl enable redis`  

```bash
sudo systemctl start redis
```

---

### 🟢 **Neo4j (Graph Storage)**  
✅ Installed and configured **Neo4j**  
✅ Opened to host with `server.default_listen_address=0.0.0.0`  
✅ Auto-restarts on failure via `systemd`  

```bash
sudo nano /etc/neo4j/neo4j.conf   # Set listen address to 0.0.0.0
sudo systemctl restart neo4j
```

---

## 🧠 3. AI Model Inference (llama.cpp)  

### 🤖 **llama.cpp (CPU-only Inference)**  
✅ Built from source with local model integration  
✅ Benchmarked **3B model** at **~253 tokens/sec**  
✅ Exposed `llama-server` on all interfaces (`0.0.0.0`)  
✅ Works with Redis for **RAG-style document Q&A**  

```bash
llama-server --host 0.0.0.0
```

---

## 🛡 4. Security & Resilience  

✅ Hardened the WSL2 Debian environment:  
- Disabled **root SSH login**  
- Enabled **firewall (UFW)** and **Fail2Ban**  
- Enabled **unattended security upgrades**  

✅ Ensured service resilience:  
- All key services auto-restart via `systemd`  
- Redis and Neo4j recover from crash or reboot  

```bash
sudo systemctl enable redis neo4j
```

> 🔍 See `MANAGE.md > Service Management` for logs and status checks.

---

## 🚀 5. Running the Full Stack  

Use the all-in-one checker to ensure all services are up:

```bash
./scripts/check.sh
```

This will:  
✅ Start `redis`, `neo4j`, `llama-server`, `embed-server`, `redis-worker`, and `http-server`  
✅ Monitor & restart them automatically  
✅ Enable access from your Windows browser or tools  

---

## 📊 6. Performance Benchmarks  

### 🧪 Test Environment  
- **CPU**: AMD Z1 Extreme (4 Cores)  
- **RAM**: 4GB  
- **Disk**: 20GB SSD  
- **OS**: Debian on WSL2  
- **GPU**: None (CPU-only inference)  

### 📈 Model Performance  

| Model                 | Tokens/sec | RAM Usage |
|----------------------|------------|-----------|
| **LLaMA 3B Q8_0**     | **253 t/s** | ~900MB    |
| **Mistral 7B Q4_K_S** | ~6 t/s     | ~4GB      |
| **LLaMA 13B Q8_0**    | ~2 t/s     | ~10GB     |

> 🧠 Performance will vary based on WSL config and CPU throttling.  

---

## 🔜 Next Steps  

✅ Run queries through Redis-backed RAG pipeline  
✅ Extend with **LangChain workflows** or **custom embedding sources**  
✅ Use [MANAGE.md](./MANAGE.md) to debug, monitor, and tune system performance  

---

This setup is now **fully optimized for low-end devices** running **CPU-only inference**.