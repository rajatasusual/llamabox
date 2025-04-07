# ⚠️ FAQ & Troubleshooting: Automation and Setup Considerations

This FAQ outlines common blockers, caveats, and best practices when automating or maintaining the **Llamabox** setup on **WSL2 + Debian**.

---

## ⚙️ Setup Considerations

### 1. 🧩 Systemd in WSL2  
- **Issue**: WSL2 doesn’t enable `systemd` by default, breaking `systemctl`, `journalctl`, etc.  
- **Fix**: Add the following to `/etc/wsl.conf` and restart WSL:  
  ```ini
  [boot]
  systemd=true
  ```

> 🔍 See `MANAGE.md > Service Management` for working with `systemctl` and `journalctl`.

---

### 2. 🔐 Sudo & Privileges  
- **Issue**: Many commands require `sudo`, and prompts can halt automation.  
- **Fixes**:  
  - Enable **passwordless sudo** if security policy allows  
  - Or run the script as root inside the distro  
  - Include `sudo -v` early in scripts to cache credentials

---

### 3. 🌐 Network Dependencies  
- **Issue**: Setup pulls from GitHub, package repos, and model hosts.  
- **Risks**:  
  - Downtime or URL changes  
  - Firewalls blocking access  
- **Fix**:  
  - Validate URLs beforehand  
  - Add retry logic or mirrors as fallback

---

### 4. 🏗️ Build Resources & Time  
- **Issue**: Compiling `llama.cpp` or processing models consumes CPU and RAM  
- **Symptoms**:  
  - Build hangs or fails in low-RAM systems  
- **Fixes**:  
  - Reduce parallel jobs: `make -j$(nproc --ignore=1)`  
  - Monitor with `htop` or `vmstat` (see `MANAGE.md > System Info`)  

---

### 5. 🛑 Manual Interventions  
- **Issue**: Certain components may require manual steps (e.g., license acceptance)  
- **Fix**:  
  - Document these steps  
  - Pre-download models or use scripted alternatives

---

### 6. 📁 Path Hardcoding  
- **Issue**: Scripts may assume fixed usernames or paths  
- **Fix**:  
  - Use `$HOME`, `$USER`, and dynamic paths wherever possible  
  - Expose config values via `.env` or variables at the top of scripts

---

## 🤖 Automation & Startup Reliability

### 1. ⏳ Race Conditions & Service Startup  
- **Issue**: Services like Neo4j may take longer than expected to become available  
- **Fix**:  
  - Add retry loops for service health checks  
  - Avoid fixed sleep times; use status-based checks

```bash
until systemctl is-active --quiet neo4j; do sleep 1; done
```

---

### 2. 🔌 Port Conflicts  
- **Issue**: Required ports (e.g., `6379`, `7474`, `11434`) might already be in use  
- **Fixes**:  
  - Use `ss -ltnp` or `netstat -tuln` to check port usage  
  - Log bind errors and provide fallbacks

---

### 3. 🧠 llama-server Configuration  
- **Issue**: `llama-server` won't run if model paths or bindings are misconfigured  
- **Fix**:  
  - Ensure model path is valid  
  - Use `--host 0.0.0.0` to bind for external access  
  - Validate model load logs or test with a minimal prompt

---

### 4. 📜 Logging & Monitoring  
- **Issue**: Services failing silently can go unnoticed  
- **Fixes**:  
  - Redirect output to logs using `nohup` or systemd journal  
  - Enable monitoring via `journalctl -u <service>`  

---

### 5. 🔄 Auto-Restart & Resilience  
- **Issue**: Without `systemd`, crashed services won’t recover  
- **Fix**:  
  - Ensure `systemd` is enabled (see above)  
  - Use `systemctl enable` for key services like Redis, Neo4j, and llama-server  

---

## ✅ Summary

| Category            | Common Issue                  | Fix / Recommendation                                 |
|---------------------|-------------------------------|------------------------------------------------------|
| Systemd             | Not enabled by default        | Add `[boot]\nsystemd=true` to `/etc/wsl.conf`        |
| Sudo Prompts        | Blocks automation             | Use passwordless sudo or run as root                 |
| Network Access      | External URLs can fail        | Validate URLs, add retries                           |
| Resources           | Low CPU/RAM causes crashes    | Monitor system, reduce `make` threads                |
| Ports               | Conflicts prevent service start | Check ports with `ss`, add fallback ports           |
| Logs                | No visibility into failures   | Use `journalctl`, log output from scripts            |
| Manual Steps        | EULA or missing files         | Document, pre-download models                        |
