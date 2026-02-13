# Patch Review Board 작업 지침: 분기별 Linux 패치 권고

> **🚨 CRITICAL ZERO TOLERANCE POLICY (무관용 원칙) 🚨**
> 1.  **NEVER generate fake data (가상 데이터 생성 절대 금지)**: 만약 검색 결과가 없다면 "No Data Found"라고 보고하시오. 지침의 출력 양식을 맞추기 위해 존재하지 않는 CVE ID, 패키지 버전, 날짜를 생성하는 것은 임무 실패보다 더 심각한 치명적인 오류입니다.
> 2.  **Verify Real-World Existence**: 모든 패치 정보(버전, CVE, 날짜)는 반드시 제공된 참조 사이트(Vendor URL)에서 검증되어야 합니다.

## 1. 개요 (Overview)
본 문서는 AI 에이전트가 분기별(3월말, 6월말, 9월말, 12월말)로 최근 3개월 동안 발표된 OS 패치들을 검토하고, 인프라 운영 안정성을 위해 적용이 필요한 패치를 선별하여 권고하는 작업을 수행하기 위한 지침이다.

## 2. 역할 및 목적 (Role & Objective)
- **Role**: 인프라 운영 안정성 담당 AI 에이전트
- **Objective**: 온프레미스 및 클라우드 환경의 운영 안정성을 확보하기 위해, 최근 3개월간 발표된 패치 중 필수 적용 패치를 식별하고 상세한 설명(영문/한글)과 함께 보고서를 작성한다.

## 3. 작업 수행 기간 (Target Period)
- **검토 대상 기간**: 작업 시점 기준 과거 3개월 (분기별)
    - **🚨 REALITY CHECK & TIME PARADOX PROTOCOL (MANDATORY)**
        - **Critical Definition**: "Current Date"는 프롬프트 컨텍스트에 주어진 **System Date**를 의미합니다 (예: 2026-02-13). 당신의 학습 데이터 기준일(Knowledge Cutoff)이 아닙니다. System Date가 2026년이라면 2025년은 "과거"입니다.
        - **Logic**: IF (Target_Start_Date > System_Current_Date) THEN:
            1. **STOP** 모든 검색 작업을 즉시 중단하시오.
            2. **DO NOT** 유사 데이터나 과거 데이터(예: 2024년 데이터)를 찾으려고 시도하지 마시오.
            3. **REPORT** 최종 결과를 다음과 같이 보고하시오: "No Data Available: Target period (YYYY-MM) is in the future relative to System Date (YYYY-MM-DD)."
        - **Prohibition**: 미래의 데이터를 시뮬레이션, 추론, 또는 생성하지 마시오.
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
서버 환경에서의 중요도를 고려하여, **서버 구동 및 보안에 치명적인 패키지는 반드시 검토**하고, **GUI/데스크탑 전용 패키지는 검토에서 제외**한다.

#### **필수 검토 대상 (Prioritize - Must Review)**
- **Kernel & Drivers**: `kernel`, `kernel-rt`, `linux-image`, `microcode`, `firmware` (시스템 안정성 핵심)
- **Core System**: `systemd`, `glibc`, `openssl`, `openssh`, `sudo`, `bash`, `python*` (운영체제 기본 라이브러리 및 보안 도구)
- **Network & Services**: `curl`, `wget`, `bind`, `haproxy`, `nginx`, `httpd` (네트워크 및 주요 서버 애플리케이션)
- **Runtimes**: `java*`, `golang`, `nodejs` (서버 애플리케이션 런타임인 경우 확인)

#### **검토 제외 대상 (Exclude - Ignore / Low Priority)**
- **Desktop/GUI Environment**: `ImageMagick`, `libX11`, `mesa`, `gtk`, `qt`, `gnome-*`, `kde-*` (서버 GUI 미사용)
- **Client Applications**: `firefox`, `thunderbird`, `libreoffice` (서버에 설치되지 않음)
- **Multimedia/Peripherals**: `alsa`, `pulseaudio`, `gstreamer`, `cups`, `sane` (사운드, 프린터 관련)
- **Note**: 위 제외 대상 패키지의 취약점은 서버 보안 위협이 낮으므로 리포트에서 생략한다.

## 5. 분야별 상세 검토 방법 (Detailed Execution Steps)

> **⚠️ 검색 출처 제한 (Strict Source Restriction)**
> 정보 수집은 반드시 아래 명시된 **각 OS별 공식 벤더 사이트(Official Vendor Pages)** 만을 사용해야 합니다.
> Google, Bing 등 **외부 검색 엔진을 사용하여 정보를 찾지 마십시오.**

> **전략적 실행 (Strategic Execution)**
> 한 번의 프롬프트로 모든 OS를 조사하려고 시도하지 마시오. 복잡도를 낮추고 정확도를 높이기 위해 **OS별로 작업을 나누어 순차적으로 진행**하는 것을 강력히 권장한다.
> 1. RHEL 조사 및 결과 출력
> 2. Ubuntu 조사 및 결과 출력
> 3. Oracle Linux 조사 및 결과 출력

> **⚠️ DYNAMIC PAGE HANDLING (필수 기술 지침)**
> RHEL 및 Oracle Linux 등 일부 벤더 사이트는 **SPA(Single Page Application)** 또는 동적 검색 폼으로 구성되어 있습니다.
> - **DO NOT USE `web_fetch` (HTTP GET)**: 단순 URL 조회 시 빈 페이지(Shell)만 반환되므로 "No Data"로 오판하게 됩니다.
> - **MUST USE Browser Tools**: 반드시 `browser_subagent` 등 브라우저 제어 도구를 사용하여 **페이지 로딩 대기 -> 필터 입력 -> 검색 버튼 클릭** 과정을 수행해야 합니다.

> **🚨 BROWSER TOOL FAILURE CONTINGENCY (비상 프로토콜)**
> 만약 `browser_subagent` 또는 `read_browser_page` 도구가 시스템 오류로 인해 실패(Error/Timeout)할 경우에 한하여, 다음의 **제한적 웹 검색(Restricted Web Search)**을 허용합니다.
> - **조건**: 반드시 `web_search`를 사용하되, `site:` 연산자로 도메인을 제한해야 함.
> - **RHEL**: `site:access.redhat.com "RHEL 9" "Security Advisory" after:2025-11-01`
> - **Ubuntu**: `site:ubuntu.com/security/notices "22.04 LTS" "2025-11"` (미래 날짜 경고가 있어도 내용이 유효하면 수집)
> - **Oracle**: `site:linux.oracle.com OR site:oracle.com "ELSA-2025" "Oracle Linux 9"`
> - **검증**: 검색된 URL이 공식 벤더 도메인인지 반드시 확인 후 데이터를 추출하시오.

### 5.1. Red Hat Enterprise Linux (RHEL)
1. **정보 수집 (Information Gathering)**: 반드시 [Red Hat Errata Search](https://access.redhat.com/errata-search) 페이지를 사용하여 검색한다. (외부 검색 금지)
    - **기술적 주의사항 (Technical Note)**: 이 페이지는 동적 폼입니다. `read_url`을 사용하지 말고, **브라우저 도구**를 사용하여 페이지에 접속한 후 폼이 로드될 때까지 기다려야 합니다.
    - **검색 전략 (Search Strategy)**: 미래 날짜(예: "Jan 2026") 검색은 반드시 실패하므로 시도하지 마십시오. 만약 특정 날짜 쿼리가 결과를 반환하지 않으면, **임의로 과거 연도(예: 2024)를 검색하지 말고**, 즉시 "No Data Found"를 확인하고 종료하십시오.
2. **검색 필터 설정 (Filter Settings)**:
    - **Product**: "Red Hat Enterprise Linux"
    - **Variant**: 다음 4가지 Variant에 대해 각각 검색
        - "Red Hat Enterprise Linux for x86_64"
        - "Red Hat Enterprise Linux for SAP Solutions for x86_64"
        - "Red Hat Enterprise Linux for SAP Applications for x86_64"
        - "Red Hat Enterprise Linux High Availability for x86_64"
    - **Version**: "10, 9, 8"
    - **Architecture**: "x86_64"
    - **Advisory Type**: "Bug Fix", "Security Advisory"
3. **상세 검색 방법 (Detailed Search Method)**:
    1.  [Red Hat Errata Search](https://access.redhat.com/errata-search) 접속
    2.  **Keyword**: 공란으로 두거나 "latest" 입력
    3.  **Filter By**:
        -   **Product**: `Red Hat Enterprise Linux` 선택
        -   **Version**: `9` 또는 `8` 등 타겟 버전 선택
        -   **Architecture**: `x86_64` 선택
        -   **Type**: `Security Advisory` 와 `Bug Fix Advisory` 체크
    4.  **Filter** 버튼 클릭
    5.  결과를 **Date** (내림차순) 정렬하여 최신 항목부터 검토
4. **중복 제거 (Deduplication)**: Product, Variant 별로 검색된 패치가 동일할 경우 하나만 선택한다.
4. **기간 필터링 (Period Filtering)**: "Updated date" 기준 최근 3개월 이내 패치만 대상으로 한다.
5. **심각도 선별 (Severity Filtering)**: Red Hat 분류 기준 "Critical", "Important" 패치만 선별한다.
6. **최신성 유지 및 설명 통합 (Version Control & Description)**: 
    - 동일한 패키지(예: kernel)에 대한 패치가 여러 건일 경우, **가장 최신 버전**의 패치 하나만 선택한다.
    - 단, 설명(`Patch Description`, `한글 설명`)에는 해당 분기 내에 포함된 이전 버전 패치들의 주요 변경/개선 내용도 함께 요약하여 포함해야 한다.
7. **내용 분석 및 선정 (Analysis & Selection)**:
    - Advisory 세부 페이지의 "Description" 섹션을 분석한다.
    - "Bug Fix(es) and Enhancement(s):" 또는 "Security Fix(es):" 내용을 확인하여 [4. 패치 권고 기준]에 부합하는지 판단하여 선정한다.
8. **검토 대상 확인 (Target Checking)**: [4.2. 검토 대상 패키지]에 정의된 모든 패키지를 대상으로 하며, 특히 커널 외에도 시스템 성능, 네트워크, 파일시스템, 보안 등 운영에 영향을 줄 수 있는 패치를 누락 없이 검토한다.

### 5.2. Ubuntu LTS
1. **정보 수집 (Information Gathering)**: 반드시 [Ubuntu Security Notices](https://ubuntu.com/security/notices) 페이지를 사용하여 검색한다. (외부 검색 금지)
2. **검색 필터 설정 (Filter Settings)**:
    - **Releases**: 현재 지원되는 LTS 버전 (Ubuntu Pro 전용 제외)
        - 예: "24.04 LTS noble", "22.04 LTS jammy"
    - "Apply filters"를 적용한다.
3. **상세 검색 방법 (Detailed Search Method)**:
    1.  [Ubuntu Security Notices](https://ubuntu.com/security/notices) 접속
    2.  **Filter** 설정:
        -   **Select Release**: `Ubuntu 24.04 LTS` 또는 `22.04 LTS` 등 타겟 버전 선택
        -   **Start/End Date**: 타겟 기간 설정 (예: `2025-11-01` ~ `2026-02-01`)
    3.  **Apply filters** 버튼 클릭하여 결과 조회
4. **기간 필터링 (Period Filtering)**: "Publication date" 기준 최근 3개월 이내 패치만 대상으로 한다.
4. **내용 분석 및 선정 (Analysis & Selection)**:
    - "CVE ID" 및 상세 내용을 확인하여 [4. 패치 권고 기준]에 부합하는지 판단하여 선정한다.
    - 동일 패키지(예: linux-image)의 경우, 분기 내 최신 패치만 선택하되 이전 패치들의 주요 수정 사항도 설명에 포함한다.
5. **검토 대상 확인 (Target Checking)**: [4.2. 검토 대상 패키지]를 준수하여 커널 외 주요 시스템 패키지(systemd, openssl 등)의 보안 패치도 포함하여 검토한다.

### 5.3. Oracle Linux
1. **정보 수집 (Information Gathering)**: 반드시 [Oracle Linux Security](https://linux.oracle.com/security) 페이지를 사용하여 검색한다. (외부 검색 금지)
    - **기술적 주의사항 (Technical Note)**: 이 페이지는 데이터를 동적으로 로딩합니다. 브라우저 도구를 사용하여 접속 후 목록이 나타날 때까지 충분히 대기하십시오. `web_fetch` 결과가 비어있다고 해서 데이터가 없는 것이 아닙니다.
2. **검색 설정 (Search Settings)**:
    - "Security Errata" 섹션 내에서 검색한다.
    - **버전**: Oracle Linux 10, 9, 8, 7, 6 Security Errata (주로 최신 버전을 권장한다)
    - **Advisory Type**: Bug, Security
3. **상세 검색 방법 (Detailed Search Method)**:
    1.  [Oracle Linux Security](https://linux.oracle.com/security) 접속
    2.  **Security Errata** 탭 선택
    3.  **검색 방식**:
        -   브라우저 찾기 기능(`Ctrl+F`)을 사용하여 `ELSA-[Year]` 형식으로 검색
        -   또는 **Release Date** 컬럼을 확인하여 해당 월의 패치 식별
    4.  `Oracle Linux 9` 또는 `8`에 해당하는 Advisory 식별
4. **기간 필터링 (Period Filtering)**: "Release Date" 기준 최근 3개월 이내 패치만 대상으로 한다 ("Updated date" 아님).
4. **내용 분석 및 선정 (Analysis & Selection)**:
    - Advisory (예: `ELSA-2026-####`) 상세 페이지의 "Description"을 분석한다.
    - "Updated Packages" 목록을 확인한다 (Architecture: `x86_64`).
    - 수정된 버그 내용을 확인하여 [4. 패치 권고 기준]에 부합하는지 판단하여 선정한다.
5. **최신성 유지 및 설명 통합 (Version Control & Description)**:
    - 동일 패키지의 경우 분기 내 최신 패치만 선택하되, 이전 패치들의 주요 수정 사항도 설명에 포함한다.
6. **검토 대상 확인 (Target Checking)**: [4.2. 검토 대상 패키지]에 명시된 kernel, systemd, glibc 등 모든 핵심 패키지를 대상으로 검토한다.

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
