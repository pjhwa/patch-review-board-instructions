# OS 패치 보안 권고 자동화 - 개발 일지

## 배경 (Context)

본 문서는 Red Hat Enterprise Linux (RHEL), Oracle Linux (UEK), Ubuntu LTS 배포판에 대한 자동화된 OS 패치 보안 권고 수집 시스템의 구현 과정을 추적합니다. 목표는 수동 벤더 사이트 검색을 대체하여 신뢰할 수 있는 자동화된 일괄 수집(2025년 11월 ~ 2026년 2월) 체계를 구축하는 것입니다.

---

## 기술적 배경

### 초기 과제: 검색 쿼리의 한계

기존 `PRB_Instruction-Linux.md`는 패치를 찾기 위해 웹 검색 쿼리에 의존했습니다. 이 접근 방식에는 심각한 결함이 있었습니다:
- **불안정한 인덱싱**: 검색 엔진이 모든 벤더 권고 페이지를 일관되게 인덱싱하지 않음
- **속도 제한(Rate Limiting)**: 잦은 검색이 봇 차단 조치를 유발함
- **불완전한 커버리지**: 최신 권고가 검색 결과에서 누락되는 경우가 잦음
- **시계열 제어 불가**: 게시일 기준으로 확실하게 필터링하기 어려움

### 해결책: 일괄 처리(Batch Processing) 전략

검색 쿼리 대신 **직접적인 벤더 소스 파싱**을 구현했습니다:
- **Red Hat**: 에라타 검색 페이지네이션 스크래핑 (10페이지, 날짜 필터링)
- **Oracle**: 공식 메일링 리스트 아카이브 파싱 (`oss.oracle.com/pipermail/el-errata`)
- **Ubuntu**: 보안 공지(USN) 웹 스크래핑 (30페이지, LTS 필터링)

---

## 인프라 설정

### OpenClaw 게이트웨이 수정 (v7)

**문제점**: OpenClaw 게이트웨이가 `localhost`에만 바인딩되어 외부 Playwright 스킬 실행이 불가능함.

**해결책**: 포트 시프트(Port Shift) + 프록시 전략
```bash
# apply_openclaw_fix_v7.sh
ORIGINAL_PORT=21000
NEW_PORT=21100
# 게이트웨이를 21100으로 이동하고, 21000에 리버스 프록시 생성
```

**검증**: `curl http://localhost:21000/health` → `{"status":"healthy"}`

### Playwright 스킬 설치

**플랫폼**: Linux (tom26 서버)
**방법**: 직접 npm 설치 (고장난 `oc skill` CLI 우회)

```bash
# 설치 단계 (INSTALL_PLAYWRIGHT_SKILL_LINUX.md)
cd ~/.openclaw/workspace
npm init -y
npm install playwright
npx playwright install
sudo npx playwright install-deps  # 시스템 의존성
```

**확인**:
```bash
node -e "const {chromium} = require('playwright'); (async()=>{const b=await chromium.launch(); await b.close();})()"
```

---

## 배치 수집 스크립트 진화 과정

### v1-v3: 초기 프로토타입
- 기본적인 Red Hat 스크래핑 (2페이지만)
- Oracle 동적 웹사이트 시도 (APEX 타임아웃으로 실패)

### v4: Oracle 디버깅 단계
- `debug_oracle.js`를 생성하여 Oracle 보안 페이지 검사
- 메인 페이지가 버전별 APEX 애플리케이션으로 링크됨을 발견
- 동적 스크래핑은 신뢰성이 떨어짐(networkidle 타임아웃)을 확인

### v5: Oracle 메일링 리스트 전환 ✅

**전략적 결정**: Oracle에 대해 "신뢰할 수 있는 피드(Trusted Feed)" 접근 방식으로 전환.

**소스**: 공식 Oracle Linux Errata 메일링 리스트 아카이브
- URL: `https://oss.oracle.com/pipermail/el-errata/`
- 구조: 월별 아카이브 (`2025-November/date.html` 등)
- 필터링: 제목에 "Unbreakable Enterprise Kernel" (UEK) 포함 여부

**구현**:
```javascript
// 대상 월별 반복
for (const month of ['2025-November', '2025-December', '2026-January', '2026-February']) {
    const url = `${baseUrl}/${month}/date.html`;
    // <li><a> 요소 파싱, "UEK" 필터링
    // ELSA-YYYY-NNNN ID 추출
}
```

**결과**: **64개 UEK 권고** 수집 성공

**장점**:
- 공식 공지 채널 (높은 신뢰성)
- 정적 HTML (자바스크립트 렌더링 이슈 없음)
- 웹사이트 리디자인에 영향을 받지 않음

### v6: Red Hat 커버리지 확장 ✅

**문제 식별**: 사용자가 3개월간 Red Hat 권고가 47개뿐인 점을 의심스럽게 여김.

**원인**: 스크립트가 2페이지(최대 200개)까지만 긁도록 하드코딩되어 있었으며, 대부분 2026년 2월 데이터였음.

**해결책**: 날짜 기반 스마트 페이지네이션
- 2페이지 → **10페이지** (1,000개 수용 가능)로 증설
- **조기 종료(Early Termination)** 구현: `2025-11-01` 이전 권고를 만나면 중단
- 필터링 로직: 대상 기간 내의 권고만 저장

**구현**:
```javascript
const MAX_REDHAT_PAGES = 10;
const TARGET_START_DATE = new Date('2025-11-01');

for (let i = 1; i <= MAX_REDHAT_PAGES && shouldContinue; i++) {
    // ... 페이지 수집 ...
    const oldestDate = parseDate(pageAdvisories[pageAdvisories.length - 1].dateStr);
    if (oldestDate < TARGET_START_DATE) {
        console.log(`페이지네이션 중단 - ${TARGET_START_DATE} 도달`);
        shouldContinue = false;
    }
}
```

**결과**: **255개 Red Hat 권고** (47개에서 5배 증가)

### v7: Ubuntu RSS 추가 ⚠️

**초기 접근**: Ubuntu 공식 RSS 피드 (`https://ubuntu.com/security/notices/rss.xml`) 활용

**구현**:
- RSS XML fetch, `<item>` 요소 추출
- LTS 버전 언급(22.04, 24.04) 필터링
- 날짜 범위 필터링 (2025.11 - 2026.02)

**결과**: **8개 Ubuntu 권고** (지나치게 적음)

**발견**: RSS 피드는 전체 3개월 아카이브가 아니라 **최신 10~20개 항목**만 제공함.

### v8: Ubuntu 웹 스크래핑 (현재) 🔄

**문제**: 3개월간 8개는 말이 안 됨.

**조사**:
- Ubuntu Security Notices 사이트: `https://ubuntu.com/security/notices`
- 전체 권고 수: **10,263개**
- 페이지네이션: `?offset=0` (1페이지), `?offset=10` (2페이지)...

**해결책**: 페이지네이션 기반 웹 스크래핑 (Red Hat과 유사)

**구현**:
```javascript
const MAX_UBUNTU_PAGES = 30; // 약 300 USN 항목

for (let i = 0; i < MAX_UBUNTU_PAGES && shouldContinue; i++) {
    const offset = i * 10;
    const url = `${baseUrl}?offset=${offset}`;
    
    // USN-YYYY-NNNN 링크 추출
    // 각 USN의 상세 페이지 fetch
    // 내용 중 LTS 버전(22.04, 24.04) 포함 여부 필터링
    // 게시일(2025.11 - 2026.02) 필터링
}
```

**결과**: 실행 중 (예상: 50~100개 이상의 LTS 권고)

---

## 수집 결과 (현재 상태)

### 확정된 결과 (v7 기준)
- **Red Hat**: 255개 권고 (2025.11 - 2026.02)
- **Oracle UEK**: 64개 권고 (메일링 리스트)
- **Ubuntu LTS**: 8개 권고 (RSS - 불완전함 확인됨)

---

## 주요 교훈 및 설계 결정

### 1. 신뢰할 수 있는 피드 > 동적 스크래핑

**Oracle 사례**: 복잡한 APEX 애플리케이션을 스크래핑하는 대신 공식 메일링 리스트 아카이브를 파싱했습니다.
- 더 신뢰할 수 있음 (정적 HTML)
- 공식적으로 관리됨
- UI 변경에 강함

### 2. 날짜 기반 조기 종료 (Early Termination)

**Red Hat & Ubuntu**: 무작정 모든 페이지를 긁는 대신:
- 게시일 내림차순 정렬 활용
- 목표 시작일 이전의 권고를 만나면 즉시 중단
- 불필요한 처리 및 API 부하 감소

### 3. RSS 피드는 불완전하다

**교훈**: RSS 피드는 전체 아카이브가 아니라 최신 항목만 제공하는 경우가 많습니다. 과거 데이터를 수집할 때는 RSS에 의존하기 전 피드의 깊이를 반드시 확인해야 합니다.

---

## 파일 산출물

- `batch_collector.js` (v8): 3개 벤더 통합 수집기
- `patch_preprocessing.py`: 데이터 전처리 및 필터링
- `GUIDE.md`: 자동화 가이드 (심층 분석)
- `README.md`: 프로젝트 개요 및 빠른 시작

---

## 변경 이력 (Revision History)

- **2026-02-13 06:00** - 초기 로그 (v1-v5 문서화)
- **2026-02-13 15:30** - v6 (Red Hat 확장) 및 v7 (Ubuntu RSS) 추가
- **2026-02-13 15:56** - v8 (Ubuntu 웹 스크래핑 전환) 추가, 전략 테이블 확정
- **2026-02-19 11:25** - **Iteration 4 (Final)**: `patch_preprocessing.py` 구현 (엄격한 가지치기 및 집계). "기계적 준비"와 "실제 AI 리뷰" 워크플로우 분리.
- **2026-02-19 17:00** - **Iteration 5 (Final Polish)**:
    - `patch_preprocessing.py` 고도화: Red Hat `Affected Products` 파싱 추가로 RHEL 버전 및 OCP 전용 권고 정확 식별.
    - `SKILL_PatchReviewBoard.md` 작성: AI 에이전트를 위한 상세 리뷰 가이드라인(포함/제외 기준, 한/영 설명 생성 등) 정립.
    - 최종 산출물 검증: `patch_review_final_report.csv` (16건의 핵심 패치, 규격 완벽 준수) 생성 확인.
