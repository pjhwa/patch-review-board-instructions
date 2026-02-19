# 🛡️ OS 패치 리뷰 보드(PRB) 자동화

> **보안 권고 자동 수집, 분석 및 보고 파이프라인**

이 프로젝트는 수작업으로 진행되던 OS 패치 리뷰 과정을 완전 자동화된 워크플로우로 대체합니다. 벤더 소스에서 보안 권고를 수집하고, 핵심 인프라 관점에서 필터링한 후, AI를 활용해 의사결정 가능한 수준의 리뷰 보고서를 생성합니다.

## 🚀 핵심 기능

*   **멀티 벤더 수집**: **Red Hat** (포털), **Oracle Linux** (메일링 리스트), **Ubuntu LTS** (USN 공지)에 대한 자동화된 스크래핑을 지원합니다.
*   **지능형 전처리**:
    *   **화이트리스트/블랙리스트**: 불필요한 패키지(데스크탑 앱 등)를 자동 제외하고, 핵심 인프라(Kernel, glibc, systemd, 컨테이너 런타임 등)에 집중합니다.
    *   **문맥 기반 파싱**: 정확한 `dist_version` 추출(예: RHEL 9와 OpenShift 구분) 및 복잡한 버Versioning 로직을 처리합니다.
    *   **집계(Aggregation)**: 동일 구성요소에 대한 다수의 업데이트를 그룹화하여 "최신 상태" 위주의 통합 뷰를 제공합니다.
*   **AI 기반 분석**: 특화된 AI 스킬(`SKILL_PatchReviewBoard.md`)을 사용하여 장애 메커니즘(시스템 행, 데이터 손실, RCE)을 분석하고, 이중 언어(한/영)로 영향도 보고서를 생성합니다.

## 📂 프로젝트 구조

| 파일 | 설명 |
|---|---|
| `batch_collector.js` | **수집기 (Collector)**. Node.js + Playwright 스크립트로 원시 권고 데이터를 스크래핑합니다. |
| `patch_preprocessing.py` | **전처리기 (Refiner)**. 파이썬 스크립트로 데이터를 필터링, 중복 제거, 집계합니다. |
| `SKILL_PatchReviewBoard.md` | **두뇌 (Brain)**. AI 에이전트의 리뷰 로직 및 보고서 작성 규칙을 정의한 스킬 문서입니다. |
| `GUIDE.md` | **[심층 가이드]**. 아키텍처, 필터링 로직, 데이터 흐름에 대한 상세 설명서입니다. |
| `batch_data/` | **저장소**. 수집된 원시 JSON 파일들이 저장되는 디렉토리입니다. |

## ⚡ 빠른 시작 (Quick Start)

### 필수 요구사항
*   **Node.js** (v18+) & **Playwright**
*   **Python** (v3.9+)

### 1. 데이터 수집 (Collect)
Headless 브라우저 수집기를 실행하여 최신 권고를 가져옵니다:
```bash
npm install playwright
node batch_collector.js
```

### 2. 전처리 (Preprocess)
데이터를 정제하고 리뷰 패킷으로 집계합니다:
```bash
python patch_preprocessing.py
```
*출력: `patches_for_llm_review.json`*

### 3. AI 리뷰 (Review)
정의된 스킬을 사용하여 AI 에이전트가 최종 CSV를 생성하도록 합니다:
```python
# 에이전트는 SKILL_PatchReviewBoard.md를 읽고 JSON 데이터를 처리합니다.
# 출력: patch_review_final_report.csv
```

## 📖 문서
아키텍처, 필터링 로직, 데이터 흐름에 대한 자세한 내용은 **[자동화 연구 가이드 (GUIDE.md)](GUIDE.md)**를 참조하십시오.
