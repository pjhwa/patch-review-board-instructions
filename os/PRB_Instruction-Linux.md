# Patch Review Board Job Instruction: Quarterly Linux Patch Recomendation

## 1. 개요 (Overview)
본 문서는 AI 에이전트가 분기별(3월말, 6월말, 9월말, 12월말)로 최근 3개월 동안 발표된 OS 패치들을 검토하고, 인프라 운영 안정성을 위해 적용이 필요한 패치를 선별하여 권고하는 작업을 수행하기 위한 지침이다.

## 2. 역할 및 목적 (Role & Objective)
- **Role**: 인프라 운영 안정성 담당 AI 에이전트
- **Objective**: 온프레미스 및 클라우드 환경의 운영 안정성을 확보하기 위해, 최근 3개월간 발표된 패치 중 필수 적용 패치를 식별하고 상세한 설명(영문/한글)과 함께 보고서를 작성한다.

## 3. 작업 수행 기간 (Target Period)
- **검토 대상 기간**: 작업 시점 기준 과거 3개월 (분기별)
- **대상 제품**: Red Hat Enterprise Linux (RHEL), Ubuntu LTS, Oracle Linux

## 4. 패치 권고 기준 및 대상 (Selection Criteria & Target Scope)

### 4.1. 권고 기준 (Criteria)
다음 기준 중 하나 이상에 해당하는 패치를 "필수 권고 대상"으로 선정한다.
1. **광범위한 적용 대상**: 일반적으로 높은 비율로 발생할 수 있는 버그가 수정된 경우
2. **시스템 안정성**: 다수의 환경에서 시스템 또는 주요 애플리케이션의 Hang이나 Crash를 유발하는 버그가 수정된 경우
3. **데이터 무결성**: Data Loss (DL), Data Unavailability (DU)를 유발할 수 있는 버그가 수정된 경우
4. **하드웨어 제어**: 컨트롤러 및 하드웨어 오동작을 유발할 위험이 있는 버그가 수정된 경우
5. **이중화 실패 방지**: 기능 오류로 인해 이중화 서버(HA)의 Failover가 실패하는 버그가 수정된 경우
6. **보안 취약점**: 심각한 보안 취약점(Critical, High Severity)이 있다고 보고된 버그가 수정된 경우
7. **기타 장애 예방**: 서버나 주요 애플리케이션 중단 등 장애로 이어질 수 있는 버그가 수정된 경우

### 4.2. 검토 대상 패키지 (Target Packages)
**단순히 Kernel 패키지만 검토하는 것이 아니라**, 아래와 같이 OS 운영 및 애플리케이션 구동에 영향을 줄 수 있는 모든 주요 패키지를 포함하여 검토한다.
- **Kernel & Drivers**: kernel, firmware, device drivers (storage, network, gpu 등)
- **Core System Services**: systemd, udev, journald, cronie, dbus 등 (부팅, 서비스 관리, 로깅 관련)
- **Network Stack**: NetworkManager, iproute, bind-utils, firewalld, iptables, ethtool 등 (네트워크 연결 및 성능 저하 관련)
- **Filesystem & Storage**: lvm2, xfsprogs, multipath-tools, nfs-utils, iscsi-initiator-utils 등 (파일시스템 오류, 마운트 실패 관련)
- **Core Libraries**: glibc, openssl, python, libstd++ 등 (애플리케이션 구동 실패, 호환성 문제 관련)
- **Security & Performance**: selinux-policy, audit, sudo, tuned, irqbalance 등 (보안 위협, 성능 지연 관련)

## 5. 분야별 상세 검토 방법 (Detailed Execution Steps)

### 5.1. Red Hat Enterprise Linux (RHEL)
1. **정보 수집**: [Red Hat Errata Search](https://access.redhat.com/errata-search) 페이지 활용
2. **검색 필터 설정**:
    - **Product**: "Red Hat Enterprise Linux"
    - **Variant**: 다음 4가지 Variant에 대해 각각 검색
        - "Red Hat Enterprise Linux for x86_64"
        - "Red Hat Enterprise Linux for SAP Solutions for x86_64"
        - "Red Hat Enterprise Linux for SAP Applications for x86_64"
        - "Red Hat Enterprise Linux High Availability for x86_64"
    - **Version**: "10, 9, 8"
    - **Architecture**: "x86_64"
    - **Advisory Type**: "Bug Fix", "Security Advisory"
3. **중복 제거**: Product, Variant 별로 검색된 패치가 동일할 경우 하나만 선택
4. **기간 필터링**: "Updated date" 기준 최근 3개월 이내 패치만 대상
5. **Severity 선별**: Red Hat 분류 기준 "Critical", "Important" 패치만 선별
6. **최신성 유지 및 설명 통합**: 
    - 동일한 패키지(예: kernel)에 대한 패치가 여러 건일 경우, **가장 최신 버전**의 패치 하나만 선택한다.
    - 단, 설명(`Patch Description`, `한글 설명`)에는 해당 분기 내에 포함된 이전 버전 패치들의 주요 변경/개선 내용도 함께 요약하여 포함해야 한다.
7. **내용 분석 및 선정**:
    - Advisory 세부 페이지의 "Description" 섹션 분석
    - "Bug Fix(es) and Enhancement(s):" 또는 "Security Fix(es):" 내용을 확인하여 [4. 패치 권고 기준]에 부합하는지 판단하여 선정
8. **검토 대상 (Target Checking)**: [4.2. 검토 대상 패키지]에 정의된 모든 패키지를 대상으로 하며, 특히 커널 외에도 시스템 성능, 네트워크, 파일시스템, 보안 등 운영에 영향을 줄 수 있는 패치를 누락 없이 검토한다.

### 5.2. Ubuntu LTS
1. **정보 수집**: [Ubuntu Security Notices](https://ubuntu.com/security/notices) 페이지 활용
2. **검색 필터 설정**:
    - **Releases**: 현재 지원되는 LTS 버전 (Ubuntu Pro 전용 제외)
        - 예: "24.04 LTS noble", "22.04 LTS jammy"
    - "Apply filters" 적용
3. **기간 필터링**: "Publication date" 기준 최근 3개월 이내 패치만 대상
4. **내용 분석 및 선정**:
    - "CVE ID" 및 상세 내용을 확인하여 [4. 패치 권고 기준]에 부합하는지 판단하여 선정
    - 동일 패키지(예: linux-image)의 경우, 분기 내 최신 패치만 선택하되 이전 패치들의 주요 수정 사항도 설명에 포함한다.
5. **검토 대상 (Target Checking)**: [4.2. 검토 대상 패키지]를 준수하여 커널 외 주요 시스템 패키지(systemd, openssl 등)의 보안 패치도 포함하여 검토한다.

### 5.3. Oracle Linux
1. **정보 수집**: [Oracle Linux Security](https://linux.oracle.com/security) 페이지 활용
2. **검색 설정**:
    - "Security Errata" 섹션 내 검색
    - **버전**: Oracle Linux 10, 9, 8, 7, 6 Security Errata (주로 최신 버전 권장)
    - **Advisory Type**: Bug, Security
3. **기간 필터링**: "Release Date" 기준 최근 3개월 이내 패치만 대상 ("Updated date" 아님)
4. **내용 분석 및 선정**:
    - Advisory (예: `ELSA-2026-####`) 상세 페이지의 "Description" 분석
    - "Updated Packages" 목록 확인 (Architecture: `x86_64`)
    - "CVE ID" 및 내용을 확인하여 [4. 패치 권고 기준]에 부합하는지 판단하여 선정
5. **최신성 유지 및 설명 통합**:
    - 동일 패키지의 경우 분기 내 최신 패치만 선택하되, 이전 패치들의 주요 수정 사항도 설명에 포함한다.
6. **검토 대상 (Target Checking)**: [4.2. 검토 대상 패키지]에 명시된 kernel, systemd, glibc 등 모든 핵심 패키지를 대상으로 검토한다.

## 6. 결과물 작성 양식 (Output Format)
- **형식**: CSV (Comma-Separated Values)
- **헤더 (Header)**:
  `Category,Release Date,Vendor,Model / Version,Detailed Version,Patch Name,Patch Target,Reference Site,Patch Description,한글 설명`

- **필드 작성 규칙**:
    - **Patch Name**:
        - **RHEL**: 선택된 패키지 이름과 버전을 정확히 기입한다. (예: `kernel-4.18.0-553.82.1.el8_10`)
        - **Ubuntu**: USN의 'Packages' 섹션에 명시된 패키지 이름과 버전을 포함하여 기입한다. (예: `linux-lowlatency-hwe-6.11-6.11.0-1004.4`)
        - **Oracle Linux**: 'Updated Packages' 목록 중 Architecture가 `x86_64`인 파일명에서 `.rpm` 확장자를 제외한 이름을 기입한다. (예: `kernel-uek-5.15.0-202.135.2.el9uek`)
    - **Patch Description**: 해당 패치의 영문 설명을 작성한다. 분기 내 누적된 변경 사항을 포함한다.
    - **한글 설명**:
        - `Patch Description`의 내용을 한국어로 번역/요약하여 작성한다.
        - **존댓말 사용 금지**
        - **명사형 또는 "~임"체 사용** (간결하면서도 명확하게)
        - 담당자가 패치 필요성을 판단할 수 있도록 버그 내용과 수정 효과를 구체적으로 기술한다. (너무 요약하지 말 것)

### 작성 예시 (Example)
```csv
Category,Release Date,Vendor,Model / Version,Detailed Version,Patch Name,Patch Target,Reference Site,Patch Description,한글 설명
OS,2025-12-01,Red Hat,REDHAT,8,kernel-4.18.0-553.82.1.el8_10,kernel,https://access.redhat.com/errata/RHSA-2025:19447,"Fixes critical memory leak in slab allocator and race condition in heavy network load scenarios. Also includes prior fix for CVE-2025-1234.","슬랩 할당자의 치명적인 메모리 누수 및 과도한 네트워크 부하 시 발생하는 경쟁 상태 해결임. 이전 버전에서 수정된 CVE-2025-1234 관련 보안 패치 내용도 포함되어 시스템 안정성을 크게 향상시킴."
```
