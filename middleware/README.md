# 🔗 Middleware Patch Guidelines

> **Domain**: Infrastructure / Middleware
> **Scope**: Web Servers, WAS, Integration

This directory contains the job instructions for AI Agents to perform quarterly patch analysis for middleware and application servers.

## 📋 Target Products Scope

The following middleware platforms are within the scope of the Patch Review Board:

### Web Application Servers (WAS)
- **TmaxSoft JEUS** (Major version upgrades, Fixpacks)
- **Apache Tomcat** (Minor versions, Security patches)
- **Red Hat JBoss EAP** (Enterprise Application Platform)
- **Wildfly** (Community Edition)
- **Oracle WebLogic Server**

### Web Servers
- **TmaxSoft WebtoB**
- **Nginx** (Stable vs Mainline)
- **Apache HTTP Server** (httpd)

---

## 📄 Available Instructions

| File | Description | Target Agent |
| :--- | :--- | :--- |
| *TBD* | *Instructions for Middleware patching are under development.* | - |

---

## 🔍 Patch Selection Strategy (General)

While specific instructions are being developed, the general selection criteria for middleware prioritize:
1.  **Vulnerability Management**: Fixes for critical CVEs (e.g., Log4Shell, HTTP Request Smuggling).
2.  **Memory Leaks**: Fixes for heap exhaustion or native memory leaks in long-running JVMs.
3.  **Connection Handling**: Fixes for thread pool exhaustion or keepalive timeout bugs.
4.  **Protocol Compliance**: Fixes for HTTP/2, TLS 1.3 implementation errors.
