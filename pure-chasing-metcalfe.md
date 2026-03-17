# Patch Review Dashboard v2 — 아키텍처 개선 계획

## Context

제품이 추가될수록 `queue.ts`가 ~250줄씩 선형 증가(현재 2078줄, 7개 제품 branch + Linux 통합 branch)하고, 제품별 설정이 9개 이상의 파일에 분산되어 있어 신규 제품 추가 시 누락이 빈발한다. Linux는 현재 redhat/oracle/ubuntu 3개 vendor를 단일 `run-pipeline` job으로 처리하는 비대칭 구조다. 이를 세 가지 축(중앙 레지스트리, 일반화된 파이프라인 실행기, 제품 정의 템플릿)으로 해결하고, Linux도 다른 제품들과 동일한 구조로 맞춘다.

---

## 핵심 문제 요약

| 문제 | 현황 | 목표 |
|------|------|------|
| queue.ts 비대화 | 2078줄, 제품당 ~250줄 branch | ~450줄, 제품당 ~5줄 dispatch |
| Linux 비대칭 구조 | redhat/oracle/ubuntu가 `run-pipeline` 단일 job | `run-redhat-pipeline` 등 개별 job으로 분리 |
| 설정 분산 | 9개 파일에 vendor 문자열/경로 중복 | 1개 registry 파일 |
| 신규 제품 추가 오류 | 9+ 파일 수동 편집, 누락 빈발 | registry 1줄 + 자동 생성 |
| passthrough 미적용 | Linux에만 있음, 다른 제품은 없음 | 모든 제품에 generic passthrough 적용 |
| RAG exclusion 비일관 | Linux = prompt injection, 나머지 = file hiding | ProductConfig로 통일 관리 |
| CSV BOM 불일치 | mariadb/windows만 `\uFEFF`, ceph/vsphere 없음 | registry `csvBOM` 필드로 일관화 |
| `category: 'ceph'` 버그 | ceph run route가 `'ceph'`로 잘못 설정 | `'storage'`로 수정 |

---

## Linux 파이프라인 심층 분석 결과

### 현재 Linux의 두 가지 고유 메카닉

**1. RAG Exclusion (Prompt Injection 방식)**
- `query_rag.py`를 호출해 이전에 수동 제외된 패치 목록을 조회
- AI 프롬프트에 `CRITICAL INSTRUCTION: ... EXCLUDED ...` 형태로 주입
- 다른 제품들은 파일 숨김(file hiding) 방식 사용: `normalized/` 디렉터리를 `_hidden`으로 rename

**2. Passthrough Mechanic**
- AI가 리뷰하지 못한 패치를 `criticality: 'Important'`, `decision: 'Pending'`으로 ReviewedPatch에 직접 삽입
- 데이터 유실 방지 목적 → **모든 제품에 적용해야 할 중요한 안전장치**

**3. `providers` 파라미터는 사실상 unused**
- run/route.ts에서 전달받지만 queue.ts에서 **사용되지 않음** (vestigial code)
- 실제로는 항상 3개 vendor 전체를 처리

### 일반화 결론

| 메카닉 | 일반화 가능성 | 방향 |
|--------|-------------|------|
| Passthrough | ✅ 완전 가능 + **모든 제품에 권장** | `runAiReviewLoop` 종료 후 generic passthrough 호출 |
| RAG exclusion (prompt injection) | ✅ 가능 | ProductConfig에 `ragExclusion` 옵션 추가 |
| 파일 숨김 (file hiding) | 이미 Ceph/MariaDB 등에 존재 | ProductConfig로 통일 관리 |

---

## A. 중앙 제품 레지스트리

### 파일: `src/lib/products-registry.ts`

기존 필드에 **passthrough + RAG exclusion 옵션을 추가**한 완전한 인터페이스:

```typescript
export interface ProductConfig {
  // Identity
  id: string;                      // 'redhat', 'oracle', 'ubuntu', 'mariadb' 등
  name: string;                    // 'Red Hat Enterprise Linux', 'MariaDB' 등
  vendorString: string;            // DB vendor 필드 값: 'Red Hat', 'MariaDB' 등
  category: 'os' | 'storage' | 'database' | 'virtualization';
  active: boolean;

  // 파일시스템 레이아웃
  skillDirRelative: string;        // 'os/linux-v2/redhat', 'database/mariadb' 등
  dataSubDir: string;              // 'redhat_data', 'mariadb_data' 등
  rawDataFilePrefix: string[];     // ['RHSA-', 'RHBA-'], ['PGSL-'] 등
  preprocessingScript: string;     // 'redhat_preprocessing.py', 'mariadb_preprocessing.py' 등
  preprocessingArgs: string[];     // ['--days', '90'], ['--days', '180'] 등
  patchesForReviewFile: string;    // 'patches_for_llm_review_redhat.json' 등
  aiReportFile: string;            // 'patch_review_ai_report_redhat.json' 등
  finalCsvFile: string;            // 'final_approved_patches_redhat.csv' 등

  // BullMQ
  jobName: string;                 // 'run-redhat-pipeline', 'run-mariadb-pipeline' 등
  rateLimitFlag: string;           // '/tmp/.rate_limit_redhat' 등
  logTag: string;                  // 'REDHAT' → '[REDHAT-PREPROCESS_DONE]' 자동 생성

  // AI 프롬프트 설정
  aiEntityName: string;            // 'Red Hat Linux patches', 'MariaDB database patches' 등
  aiVendorFieldValue: string;      // 'Red Hat', 'MariaDB' 등 (AI가 Vendor 필드에 출력할 값)
  aiComponentDefault: string;      // 'kernel', 'mariadb' 등 (AI가 Component 누락 시 fallback)
  aiVersionGrouped: boolean;       // true = sqlserver/windows (버전 그룹핑 방식)
  aiBatchValidation: 'exact' | 'nonEmpty';

  // RAG Exclusion 설정 (선택)
  ragExclusion?: {
    type: 'file-hiding' | 'prompt-injection';
    // file-hiding: normalizedDir을 _hidden으로 rename + patchesFile을 .hidden으로 rename
    normalizedDirName?: string;    // 'redhat_data/normalized' (file-hiding 시)
    // prompt-injection: query_rag.py 호출 후 결과를 프롬프트에 주입
    queryScript?: string;          // 'query_rag.py' (prompt-injection 시)
    queryTextSampleSize?: number;  // 프롬프트에 넣을 샘플 패치 수 (default: 3)
  };

  // Passthrough 설정 (AI가 리뷰하지 못한 패치 처리)
  passthrough: {
    enabled: boolean;
    fallbackCriticality: string;   // 'Important'
    fallbackDecision: string;      // 'Pending'
  };

  // DB 수집 필터 (products/route.ts 파일 카운트용)
  collectedFileFilter: (filename: string) => boolean;

  // 전처리 패치 → DB 스키마 매핑 콜백
  preprocessedPatchMapper: (raw: any) => object;

  // CSV BOM 여부
  csvBOM: boolean;
}
```

### 10개 제품 레지스트리 (Linux 분리 후)

```
PRODUCT_REGISTRY = [
  // OS Category (4개 → 개별 제품)
  { id: 'redhat',    vendorString: 'Red Hat',             jobName: 'run-redhat-pipeline',   ... },
  { id: 'oracle',    vendorString: 'Oracle',              jobName: 'run-oracle-pipeline',   ... },
  { id: 'ubuntu',    vendorString: 'Ubuntu',              jobName: 'run-ubuntu-pipeline',   ... },
  { id: 'windows',   vendorString: 'Windows Server',      jobName: 'run-windows-pipeline',  ... },

  // Storage Category
  { id: 'ceph',      vendorString: 'Ceph',                jobName: 'run-ceph-pipeline',     ... },

  // Database Category (3 active)
  { id: 'mariadb',   vendorString: 'MariaDB',             jobName: 'run-mariadb-pipeline',  ... },
  { id: 'sqlserver', vendorString: 'SQL Server',          jobName: 'run-sqlserver-pipeline',...},
  { id: 'pgsql',     vendorString: 'PostgreSQL',          jobName: 'run-pgsql-pipeline',    ... },

  // Virtualization Category
  { id: 'vsphere',   vendorString: 'VMware vSphere',      jobName: 'run-vsphere-pipeline',  ... },

  // Placeholders (inactive)
  { id: 'mysql',     active: false, ... },
  { id: 'mongodb',   active: false, ... },
]
```

---

## B. Linux 파이프라인 분리 (신규 작업)

### B.1 전처리 스크립트 분리 전략

**현재:** `patch_preprocessing.py`가 redhat/oracle/ubuntu_data 3개 디렉터리를 한 번에 처리.

**권장 방식: `--vendor` 인자 추가** (스크립트 1개, vendor별 호출)
```bash
python3 patch_preprocessing.py --vendor redhat --days 90
python3 patch_preprocessing.py --vendor oracle --days 90
python3 patch_preprocessing.py --vendor ubuntu --days 90
```

- 코드 중복 최소화
- 기존 공통 로직 (날짜 파싱, 컴포넌트 화이트리스트 등) 유지
- 출력 파일: `patches_for_llm_review_redhat.json`, `_oracle.json`, `_ubuntu.json`

**디렉터리 구조 (분리 후):**
```
patch-review/os/linux-v2/
├── patch_preprocessing.py          # --vendor 인자로 분기
├── SKILL.md                        # 공유 (또는 vendor별 분리)
├── redhat/
│   ├── redhat_data/               # 수집 데이터
│   └── patches_for_llm_review_redhat.json  # 전처리 출력
├── oracle/
│   ├── oracle_data/
│   └── patches_for_llm_review_oracle.json
└── ubuntu/
    ├── ubuntu_data/
    └── patches_for_llm_review_ubuntu.json
```

### B.2 SKILL.md 분리

현재 단일 `linux-v2/SKILL.md`(182줄)는 3개 vendor를 모두 다룬다. 분리 후:

**Option A (권장):** 공통 SKILL.md 유지 + vendor별 Section 추가
- `linux-v2/SKILL.md`에 `## 6. Vendor-Specific Rules` 섹션 추가
- redhat/oracle/ubuntu 각각의 특이사항 기술
- 코드 중복 최소화, 파일 1개 유지

**Option B:** vendor별 SKILL.md 생성
- `linux-v2/redhat/SKILL.md`, `linux-v2/oracle/SKILL.md`, `linux-v2/ubuntu/SKILL.md`
- 각 제품별 완전 독립적 지침
- 파일 수 증가하지만 제품 추가/수정이 독립적

→ **Option A를 먼저 적용**, 필요시 Option B로 전환.

### B.3 RAG Exclusion 처리

Linux의 `query_rag.py` prompt-injection 방식을 ProductConfig로 이관:

```typescript
// redhat ProductConfig
ragExclusion: {
  type: 'prompt-injection',
  queryScript: 'query_rag.py',
  queryTextSampleSize: 3,
}

// mariadb ProductConfig
ragExclusion: {
  type: 'file-hiding',
  normalizedDirName: 'mariadb_data/normalized',
}

// ceph/vsphere (현재 file-hiding 미적용 → 추가 가능)
// ragExclusion: undefined  (RAG 없음)
```

generic `runAiReviewLoop`에서 `productCfg.ragExclusion?.type`에 따라 분기:
```typescript
if (ragExclusion?.type === 'file-hiding') {
  renameDir(normalizedDir, normalizedDir + '_hidden');
  renameFile(patchesFile, patchesFile + '.hidden');
} else if (ragExclusion?.type === 'prompt-injection') {
  ragExclusionText = await queryRagScript(skillDir, queryScript, samplePatches);
}
```

### B.4 세션 격리 (3개 Linux 제품 동시 실행 방지)

현재 `sessions.json`은 `~/.openclaw/agents/main/sessions/`에 공유된다. 3개 Linux job이 동시 실행되면 세션 오염 위험.

해결책: **`withOpenClawLock`이 이미 전역 lock을 제공** → 동시 실행은 이미 불가. 추가 조치 불필요.

---

## C. Passthrough의 모든 제품 일반화

### 현재 상태
- Linux에만 passthrough 존재 (queue.ts lines 2012-2053)
- 다른 제품은 AI가 배치를 건너뛰면 해당 패치가 ReviewedPatch에 존재하지 않음 → 데이터 유실

### 일반화 구현

`runProductPipeline`의 `ingestToDb` 이후:

```typescript
async function runPassthrough(
  job: Job,
  productCfg: ProductConfig,
  aiReviewedIds: Set<string>
): Promise<void> {
  if (!productCfg.passthrough.enabled) return;

  const missing = await prisma.preprocessedPatch.findMany({
    where: {
      vendor: productCfg.vendorString,
      issueId: { notIn: Array.from(aiReviewedIds) },
    },
  });

  if (missing.length === 0) return;
  await job.log(`[PASSTHROUGH] ${productCfg.name}: ${missing.length} patches AI-skipped → Pending`);

  for (const pp of missing) {
    await prisma.reviewedPatch.upsert({
      where: { issueId: pp.issueId },
      update: {
        criticality: productCfg.passthrough.fallbackCriticality,
        decision: productCfg.passthrough.fallbackDecision,
      },
      create: {
        issueId: pp.issueId,
        vendor: pp.vendor,
        component: pp.component || productCfg.aiComponentDefault,
        version: pp.version || 'Unknown',
        criticality: productCfg.passthrough.fallbackCriticality,
        decision: productCfg.passthrough.fallbackDecision,
        description: pp.description || '',
        koreanDescription: '',
        pipelineRunId: job.id?.toString() || 'passthrough',
      },
    });
  }
}
```

**각 제품별 passthrough 설정:**
```typescript
// 모든 제품: enabled: true 권장 (안전망)
passthrough: { enabled: true, fallbackCriticality: 'Important', fallbackDecision: 'Pending' }

// SQL Server/Windows (버전 그룹핑 → AI 필수):
passthrough: { enabled: false }  // 버전 그룹 선택이 AI의 핵심 역할이므로 passthrough 부적합
```

---

## D. queue.ts 리팩터링 (Linux 포함 전체)

### 목표: 2078줄 → ~450줄

### D.1 추출할 공통 함수

**`makeStreamRunner(skillDir, job)`**
- 7개 product별 동일한 `runXxxStream` 클로저 → 팩토리 함수 1개로 통합

**`prunePatch(obj: any)`**
- 7개 `prunePatchXxx` → 단일 함수 (fieldname fallback chain 유지)

**`runAiReviewLoop(job, productCfg, skillDir, runStream, patches, isResumeMode)`**
- RAG 블라인딩 (`productCfg.ragExclusion` 기반), 배치 반복, Zod 검증, rate-limit 처리
- `productCfg.aiVersionGrouped`로 버전 그룹핑 프롬프트 분기
- 종료 후 자동으로 `runPassthrough` 호출

**`ingestToDb(job, productCfg, patches, reviewed, isResumeMode, isAiOnly)`**
- DB 삽입/갱신 공통 처리

**`runPassthrough(job, productCfg, aiReviewedIds)`**
- 위 C항 참조

### D.2 제네릭 실행기

```typescript
async function runProductPipeline(job, productCfg, isAiOnly, isRetry): Promise<string> {
  const skillDir = getSkillDir(productCfg);
  const runStream = makeStreamRunner(skillDir, job);
  const isResumeMode = checkResumeMode(productCfg);

  if (!isResumeMode && !isAiOnly) {
    await runPreprocessing(productCfg, skillDir, runStream, job);
  }

  const { reviewed, reviewedIds } = await runAiReviewLoop(
    job, productCfg, skillDir, runStream, patches, isResumeMode
  );

  await ingestToDb(job, productCfg, patches, reviewed, isResumeMode, isAiOnly);
  await runPassthrough(job, productCfg, reviewedIds);  // 안전망

  return `${productCfg.name} pipeline success`;
}
```

### D.3 Worker dispatch (Linux 포함, 완전 통합)

```typescript
new Worker('patch-pipeline', async (job) => {
  const productCfg = PRODUCT_MAP[jobNameToProductId(job.name)];
  if (productCfg) {
    return runProductPipeline(job, productCfg, job.data.isAiOnly, job.data.isRetry);
  }
  if (job.name === 'manual-review') return runManualReview(job);
  // 더 이상 Linux 특수 케이스 없음
});
```

**Linux도 다른 제품과 동일하게 `PRODUCT_MAP` 조회로 처리** — 특수 케이스 제거.

---

## E. 분산된 vendor 매핑 대체

| 파일 | 현재 | 변경 후 |
|------|------|---------|
| `stage/[stageId]/route.ts` | `if (productId === 'X') vendor = 'Y'` | `PRODUCT_MAP[productId].vendorString` |
| `export/route.ts` | per-product 필터 + category "all" 블록 | 레지스트리 `category` 그룹핑 자동 생성 |
| `ClientPage.tsx` title 맵 | 삼항 체인 | `PRODUCT_MAP[productId].name` |
| `ClientPage.tsx` finalizeEndpoint 분기 | 제품별 분기 | 단일 generic endpoint |
| `ProductGrid.tsx` pipelineRunUrl | 분기 로직 | `PRODUCT_MAP[productId].jobName` |
| `products/route.ts` | 제품별 수집 카운트 로직 | `PRODUCT_REGISTRY` 루프 + `collectedFileFilter` |

---

## F. API 라우트 정리

### run 라우트 변경 (Linux)
현재 `/api/pipeline/run` (generic OS)에서:
- `providers = ['redhat']` → `job.name = 'run-redhat-pipeline'` 으로 enqueue
- 기존 `providers` 파라미터 활용: 선택된 vendor만 실행 가능

```typescript
// /api/pipeline/run/route.ts
for (const vendor of providers) {
  await pipelineQueue.add(`run-${vendor}-pipeline`, { isRetry, isAiOnly });
}
```

### finalize 라우트 통합 (5개 → 1개 generic)
```
POST /api/pipeline/finalize?product={productId}
```
- 경로는 `PRODUCT_MAP[productId].finalCsvFile`로 결정
- BOM은 `PRODUCT_MAP[productId].csvBOM`으로 결정
- ceph/vsphere에도 `\uFEFF` BOM 추가

---

## G. 제품 정의 스펙 템플릿 (`docs/PRODUCT_SPEC_TEMPLATE.md`)

신규 제품 추가 시 사용자가 작성하는 구조화된 문서. 8개 섹션으로 구성:

```markdown
## 1. Identity
| productId | vendorString | category | skillDirRelative |

## 2. Raw Data Format
- Source system:
- File prefix(es):
- Sample JSON: { "id": ..., "severity": ..., "issued": ... }
- Field mapping table:
  | Raw Field | Meaning | Notes |

## 3. Filtering Requirements
- Days window: N일 (--days_end 필요: Yes/No)
- KEEP 조건: (severity, env, component whitelist 등)
- DROP 조건: (오래된 항목, 제거할 필드명 등)

## 4. Grouping / Output Structure
- 개별(Individual) vs 버전그룹(Version-grouped)
- (버전그룹인 경우) 그룹 키 필드, 그룹 ID 형식, 선택 기준

## 5. Criticality Determination
- 방법: severity 필드 / 키워드 기반 / CVE 수·CVSS 기반
- Criticality 매핑 표

## 6. Data Release Pattern
- 발표 주기, 누적 vs 증분, 복수 데이터 소스 여부

## 7. AI Review Special Instructions
- Vendor 필드 정확한 값:
- Component 예시 목록:
- 설명 포함/제외 내용:
- Hallucination risk 영역:
- 제거할 raw 필드 (faq 등 대용량 반복 텍스트):
- Passthrough 필요 여부 + fallback criticality/decision:
- RAG exclusion 방식: file-hiding / prompt-injection / 없음

## 8. SKILL.md Context
- 이 제품이 조직에 중요한 이유:
- 주목해야 할 취약점 유형 TOP 3:
- AI 오판 false-positive 패턴:
- 제외 조건:
```

---

## H. SKILL.md 표준 구조

모든 SKILL.md는 아래 섹션 구조로 100줄 이상 + Section 4 존재 보장:

```
## 1. Process Workflow          (~40줄)
## 2. Data Source Reference     (~18줄, 필드 표)
## 3. Evaluation Context        (~8줄)
## 4. Strict LLM Evaluation Rules   (~30줄+)
  ### 4.1 Inclusion Criteria
  ### 4.2 Exclusion Criteria
  ### 4.3 Output Format (JSON 스키마)
  ### 4.4 General Rules
  ### 4.5 Hallucination Prevention Rules
## 5. Output Validation Rules   (~15줄)
```

Linux-v2 SKILL.md는 Section 6에 Vendor-Specific Rules 추가 (redhat/oracle/ubuntu 차이점).

---

## I. 자동화 도구

### `scripts/validate-registry.ts`
- active 제품의 skillDir 존재 확인
- preprocessingScript 존재 확인
- SKILL.md 존재 + 100줄 이상 + "## 4." 확인
- ragExclusion 설정 일관성 확인 (file-hiding이면 normalizedDirName 필수 등)

### `scripts/generate-product.ts`
spec 파일을 읽어 자동 생성:
- registry 항목 stub
- run/finalize route stub
- SKILL.md (표준 템플릿 + spec 내용)
- 전처리 스크립트 stub

---

## 구현 순서

### Phase 1 — 기반 (동작 변경 없음)
1. `src/lib/products-registry.ts` 생성 (10개 제품, Linux 3개 포함)
2. `scripts/validate-registry.ts` 작성 및 실행
3. `stage/[stageId]/route.ts`, `export/route.ts`, `ClientPage.tsx` title 맵 → 레지스트리 조회로 교체

### Phase 2 — Linux 파이프라인 분리
4. `patch_preprocessing.py`에 `--vendor` 인자 추가 (redhat/oracle/ubuntu 분기)
5. `linux-v2/SKILL.md`에 Section 6 (Vendor-Specific Rules) 추가
6. `/api/pipeline/run/route.ts` 수정: providers 루프로 vendor별 job enqueue
7. **버그 수정**: `ceph/run/route.ts`의 `category: 'ceph'` → `'storage'`

### Phase 3 — queue.ts 리팩터링
8. `makeStreamRunner` 팩토리 추출
9. `prunePatch` 통합
10. `runPassthrough` generic 함수 구현
11. `runAiReviewLoop` 추출 (RAG exclusion + passthrough 통합)
12. `ingestToDb` 추출
13. 제네릭 실행기 연결, Linux 포함 전체 제품 branch 통합
14. 제품별 파이프라인 테스트

### Phase 4 — API 라우트 통합
15. finalize 라우트 5개 → 1개 generic (`/api/pipeline/finalize?product=X`)
16. ceph/vsphere finalize에 `\uFEFF` BOM 추가
17. `ClientPage.tsx`, `ProductGrid.tsx` endpoint 업데이트

### Phase 5 — 문서화 및 도구
18. `docs/PRODUCT_SPEC_TEMPLATE.md` 생성
19. `scripts/generate-product.ts` 작성
20. `ADDING_NEW_PRODUCT.md` 업데이트

---

## 검증 방법

1. `scripts/validate-registry.ts` 실행 → 10개 제품 모두 PASS
2. Linux 3개 제품 개별 실행 → redhat/oracle/ubuntu 각각 독립적으로 동작 확인
3. 모든 제품 파이프라인 실행 → 전처리 → AI 리뷰 → passthrough → DB 적재 정상 확인
4. `/api/pipeline/stage/preprocessed?product=redhat` (oracle, ubuntu 각각)
5. `/api/pipeline/finalize?product=ceph` → CSV + `\uFEFF` BOM 포함 확인
6. `/api/pipeline/export?categoryId=os&productId=all` → Red Hat + Oracle + Ubuntu + Windows 포함
7. AI가 배치 건너뛰는 상황 시뮬레이션 → passthrough로 Pending 상태 패치 생성 확인

---

## 수정 대상 파일 목록

**수정 필요:**
- `src/lib/queue.ts` — 핵심 리팩터링 (Linux 포함 전 제품 통합)
- `src/app/api/pipeline/run/route.ts` — providers 루프로 vendor별 enqueue
- `src/app/api/products/route.ts` — 레지스트리 기반 루프
- `src/app/api/pipeline/stage/[stageId]/route.ts` — vendor 맵 교체
- `src/app/api/pipeline/export/route.ts` — vendor 맵 + category 필터
- `src/app/category/[categoryId]/[productId]/ClientPage.tsx` — title/endpoint 맵
- `src/components/ProductGrid.tsx` — pipelineRunUrl + logTag 맵
- `src/app/api/pipeline/ceph/run/route.ts` — `category: 'ceph'` → `'storage'`
- `src/app/api/pipeline/ceph/finalize/route.ts` — BOM 추가
- `src/app/api/pipeline/vsphere/finalize/route.ts` — BOM 추가
- `patch-review/os/linux-v2/patch_preprocessing.py` — `--vendor` 인자 추가
- `patch-review/os/linux-v2/SKILL.md` — Section 6 vendor-specific 추가
- `ADDING_NEW_PRODUCT.md` — 재작성

**신규 생성:**
- `src/lib/products-registry.ts`
- `docs/PRODUCT_SPEC_TEMPLATE.md`
- `scripts/validate-registry.ts`
- `scripts/generate-product.ts`
