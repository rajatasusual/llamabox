# WSL Assistant Roadmap

This roadmap outlines the planned features for WSL Assistant. While there are many exciting additions on the horizon, our immediate focus is on ensuring a robust, secure, and performant foundation.

---

## **High Priority: Robustness & Stability**

- **Performance Optimization**
  - [ ] Benchmarking under load for various AI models
  - [ ] Profiling and optimizing CPU-only inference
  - [ ] Fine-tuning resource allocation in WSL2

- **Security Hardening**
  - [ ] Advanced vulnerability testing and secure defaults review
  - [ ] Encryption for data-at-rest and in-transit (where applicable)
  - [ ] Regular security audits and patch management

- **Robust Monitoring & Logging**
  - [ ] Enhance service monitoring dashboards (resource usage, status, alerts)
  - [ ] Integrate centralized log aggregation and real-time alerting
  - [ ] Implement health checks and automated recovery routines

---

## **Core Features**

- **Web UI for Monitoring Services**
  - [ ] Dashboard for resource usage
  - [ ] Service status monitoring
  - [ ] Log viewer integration
  - [ ] Real-time updates

- **Custom WebUI for llama.cpp Server**
  - [ ] Implement WebSocket communication for live interactions
  - [ ] Develop a user-friendly chat interface
  - [ ] Add model parameter controls
  - [ ] Enable session management
  - [ ] Reference: [llama.cpp server examples](https://github.com/ggml-org/llama.cpp/tree/master/examples/server#extending-or-building-alternative-web-front-end)

- **Integration with LangChain for Extended RAG**
  - [ ] Build a document processing pipeline
  - [ ] Implement a vector store integration
  - [ ] Develop a query routing system
  - [ ] Manage a scalable knowledge base

- **Multi-user SSH with Isolated Environments**
  - [ ] Develop a robust user authentication system
  - [ ] Enable container-based isolation per user
  - [ ] Implement resource allocation controls
  - [ ] Set up shared resource management

- Extension to capture all captured data.
---

## **Deployment & Distribution**

- **Custom Linux Distro for Plug-and-Play**
  - [ ] Create a custom WSL Linux distro using WSL root filesystem tar files  
    (See [Microsoft’s guide](https://learn.microsoft.com/en-us/windows/wsl/build-custom-distro#what-are-wsl-root-filesystem-tar-files) for reference)

- **Public Access to RAG Services**
  - [ ] Enable secure access to the RAG pipeline from a public IP  
    (Implement necessary security measures such as VPNs or reverse proxies)

---

## **Future Enhancements**

- [ ] API Documentation for all services and integrations
- [ ] Community Plugins Support to extend functionality
