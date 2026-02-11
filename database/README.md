# 🗄️ Database Patch Guidelines

> **Domain**: Infrastructure / Databases
> **Scope**: Oracle, MS SQL, Open Source DBs

This directory contains the job instructions for AI Agents to perform quarterly patch analysis for database management systems.

## 📋 Target Products Scope

The following database platforms are within the scope of the Patch Review Board:

### Commercial RDBMS
- **Oracle Database** (19c, 21c, 23c)
- **Oracle Exadata** (System Software)
- **Microsoft SQL Server** (2019, 2022)
- **EPAS** (EnterpriseDB Postgres Advanced Server)

### Open Source RDBMS
- **MySQL / MariaDB**
- **PostgreSQL**

---

## 📄 Available Instructions

| File | Description | Target Agent |
| :--- | :--- | :--- |
| *TBD* | *Instructions for Database patching are under development.* | - |

---

## 🔍 Patch Selection Strategy (General)

While specific instructions are being developed, the general selection criteria for databases prioritize:
1.  **Data Integrity**: Fixes for corruption, wrong results, or recovery failures.
2.  **Security**: Critical CVEs in the database engine or listeners.
3.  **Performance**: Fixes for query optimizer bugs causing massive regressions.
4.  **Availability**: Fixes for clusterware (RAC, AlwaysOn) reliability.
