### 🚀 **Llamabox - Setup Summary**  

Here's a **high-level breakdown** of the setup process, categorized by components:  

---

## **🛠 1. System Setup (WSL & Debian)**  
✅ Install **WSL2** and **Debian** on Windows  
✅ Allocate **at least 4GB RAM & 20GB storage**  
✅ Clone the repository and run `./setup.sh`  

```sh
wsl --install -d Debian
git clone https://github.com/rajatasusual/llamabox.git
cd llamabox
./setup.sh
```

---

## **📦 2. Database & Vector Store**  

### **🔴 Redis Stack (Vector Storage)**
✅ Installed **Redis Stack** for vector embeddings  
✅ Enabled **persistent storage** for AI data  
✅ Auto-start configured with `systemctl enable redis`  

```sh
sudo systemctl start redis
```

---

### **🟢 Neo4j (Graph Database)**
✅ Installed **Neo4j** for knowledge graph storage  
✅ Exposed Neo4j to the Windows host (`server.default_listen_address=0.0.0.0`)  
✅ Auto-restart enabled  

```sh
sudo nano /etc/neo4j/neo4j.conf  # Uncomment 'server.default_listen_address=0.0.0.0'
sudo systemctl restart neo4j
```

---

## **🧠 3. AI Model (Local Inference with llama.cpp)**  

### **🤖 llama.cpp (CPU-based AI Engine)**
✅ Installed **llama.cpp** for **low-end, CPU-only AI inference**  
✅ Benchmarked **3B-parameter model** at **~253 tokens/sec**  
✅ Integrated with Redis for **RAG-based document Q&A**  
✅ Configured `llama-server` to **bind to `0.0.0.0`**  

```sh
llama-server --host 0.0.0.0
```

---

## **🛡 4. Security & Resilience**  

✅ **Security Hardened**  
   - Disabled **root SSH login**  
   - Enabled **firewall (`ufw`) and Fail2Ban**  
   - **Automatic security updates**  

✅ **Resilience & Auto-Restart**  
   - Redis & Neo4j configured for **automatic recovery**  
   - Services restart on crashes via **systemd**  

```sh
sudo systemctl enable redis neo4j
```

---

## **🚀 5. Running the Full Stack**  

To start everything in one go:  

```sh
./scripts/start.sh
```

This will:  
✅ Start **Redis**, **Neo4j**, and **llama-server** in order  
✅ Ensure **services restart** if they crash  
✅ Enable **network access** from Windows  

---

## **📊 6. Performance Benchmarks**  

### **Test Environment (WSL2 Debian)**
- **CPU**: AMD Z1 Extreme (4 Cores)  
- **RAM**: 4GB  
- **Storage**: 20GB SSD  
- **OS**: Debian  
- **GPU**: **None** (CPU-only inference)  

### **Benchmark Results**
| Model                | Tokens/sec | VRAM (MB) |
|----------------------|-----------|-----------|
| **Llama 3B Q8_0**    | **253 t/s** | **~900MB** |
| **Mistral 7B Q4_K_S** | ~6 t/s    | ~4GB      |
| **LLaMA 13B Q8_0**  | ~2 t/s    | ~10GB     |

---

## **🔜 Next Steps**  
✅ Run inference queries via Redis + Neo4j  
✅ Extend with **LangChain** for custom workflows  
✅ Monitor & tweak **resource limits for WSL**  

---

This is now **fully optimized for low-end, CPU-only devices** while maintaining **enterprise-grade AI capabilities**. 🚀