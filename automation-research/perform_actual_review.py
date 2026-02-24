import json
import csv
import re
import sys
import os

# Input file is expected in the same directory
INPUT_FILE = "patches_for_llm_review.json"
OUTPUT_FILE = "patch_review_final_report.csv"

# Keywords to identify "Critical" impact
CRITICAL_KEYWORDS = {
    "System Hang/Crash": ["panic", "hang", "deadlock", "crash", "freeze", "stuck", "halt", "general protection fault"],
    "Data Loss/Corruption": ["corruption", "data loss", "check failure", "inconsistency", "truncate", "leaked", "filesystem error", "integrity"],
    "Boot Fail": ["boot", "startup", "initramfs", "grub", "failure to start"],
    "Critical Security": ["remote code execution", "rce", "privilege escalation", "root", "arbitrary code", "auth bypass", "authentication bypass"],
    "Service Outage": ["denial of service", "dos", "segfault", "segmentation fault", "memory leak", "out of memory", "oom"]
}

def is_critical(text):
    text = text.lower()
    found_impacts = []
    
    for category, keywords in CRITICAL_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                found_impacts.append(category)
    return list(set(found_impacts))

def extract_key_sentence(text):
    """Extracts sentences containing critical keywords."""
    # Split by sentence boundaries (roughly)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    matches = []
    seen = set()
    
    for s in sentences:
        s_lower = s.lower()
        found = False
        for cat, kws in CRITICAL_KEYWORDS.items():
            for k in kws:
                if k in s_lower:
                    clean_s = s.strip()
                    if clean_s not in seen:
                        matches.append(clean_s)
                        seen.add(clean_s)
                    found = True
                    break
            if found: break
    return matches

def generate_korean_desc(patch_id, impacts, is_cumulative, history_count):
    # Fallback template
    impact_map = {
        "System Hang/Crash": "시스템 멈춤 및 크래시 방지",
        "Data Loss/Corruption": "데이터 손실 및 무결성 오류 해결",
        "Boot Fail": "부팅 실패 문제 수정",
        "Critical Security": "권한 상승 및 원격 코드 실행(RCE) 취약점 해결",
        "Service Outage": "서비스 거부(DoS) 및 메모리 누수 방지"
    }
    
    summary_parts = [impact_map[i] for i in set(impacts) if i in impact_map]
    if not summary_parts:
        summary_parts = ["시스템 안정성 및 보안 향상"]
    
    desc = ", ".join(summary_parts) + "."
        
    if is_cumulative:
        desc += f" (누적 패치 포함: {history_count}건)"
        
    return desc

def generate_english_desc(patch_id, impacts, is_cumulative):
    # Fallback template
    impact_map = {
        "System Hang/Crash": "Fixes system hang/crash issues",
        "Data Loss/Corruption": "Prevents data loss/corruption",
        "Boot Fail": "Resolves boot failures",
        "Critical Security": "Mitigates Critical Security vulnerabilities (RCE/PrivEsc)",
        "Service Outage": "Prevents Denial of Service and OOM"
    }
    
    summary_parts = [impact_map[i] for i in set(impacts) if i in impact_map]
    if not summary_parts:
        summary_parts = ["Improves system stability and security"]
        
    desc = ", ".join(summary_parts) + "."
        
    return desc

BEST_PRACTICE_DESCS = {
    "ELSA-2026-50100": {
        "en": "LTS v5.4.302 cumulative batch with 31 CVEs. Critical: tipc UAF crash (CVE-2025-40280), sctp OOB write / NULL deref causing crash (CVE-2025-40281, CVE-2025-40331), Bluetooth SCO Use-After-Free (CVE-2025-40309), btusb disconnect UAF (CVE-2025-40283), fbdev vmalloc OOB access (CVE-2025-40304, CVE-2025-40322), NFS directory readdir NULL deref crash (CVE-2025-68185), scsi tcm_loop segfault (CVE-2025-68229), net/sched NULL deref (CVE-2025-40083).",
        "ko": "LTS v5.4.302 누적 패치(31개 CVE 포함). 주요: TIPC UAF 크래시(CVE-2025-40280), sctp 범위 초과 쓰기 및 NULL 역참조 크래시(CVE-2025-40281, CVE-2025-40331), Bluetooth SCO 연결 해제 시 UAF 크래시(CVE-2025-40309, CVE-2025-40283), fbdev vmalloc 범위 초과 접근(CVE-2025-40304/40322), NFS readdir NULL 역참조 크래시(CVE-2025-68185), scsi tcm_loop 세그폴트(CVE-2025-68229) 수정."
    },
    "ELSA-2026-50061": {
        "en": "Fixes Use-After-Free in tipc (CVE-2025-40280), fs/proc UAF (CVE-2025-40271), vsock race (CVE-2025-40248), and af_alg concurrent write memory corruption (CVE-2025-39964). Includes LTS v5.4.301 stable batch: critical ext4 out-of-bounds read, sctp NULL deref (kernel crash), fbcon integer overflow, scsi/mvsas UAF fixes.",
        "ko": "TIPC UAF(CVE-2025-40280), /proc UAF(CVE-2025-40271), vsock 경쟁 상태(CVE-2025-40248)로 인한 커널 크래시 수정. af_alg에서 동시 쓰기 시 메모리 손상(CVE-2025-39964) 수정. LTS v5.4.301 안정화 패치 포함: ext4 버퍼 범위 초과 읽기, sctp NULL 역참조(시스템 크래시), fbcon 정수 오버플로우, scsi/mvsas UAF 등 시스템 안정성 수정."
    },
    "ELSA-2026-50095": {
        "en": "Fixes xfrm tunnel state Use-After-Free on destroy (CVE-2025-40215) causing kernel crash during IPSec teardown. Fixes mptcp_schedule_work() race condition (CVE-2025-40258) causing kernel crash under MPTCP load. Fixes fuse readahead reclaim deadlock (potential system hang). Fixes sunrpc TLS alert handling bugs (CVE-2025-38566, CVE-2025-38571) causing NFS/RPC connection failures.",
        "ko": "xfrm IPSec 터널 소멸 시 Use-After-Free(CVE-2025-40215)로 인한 커널 크래시 수정. MPTCP 부하 하 `mptcp_schedule_work()` 경쟁 상태(CVE-2025-40258)로 인한 커널 크래시 수정. fuse 파일시스템 미리읽기 처리 중 데드락(시스템 Hang) 수정. sunrpc TLS 알림 처리 버그(CVE-2025-38566/38571)로 인한 NFS/RPC 연결 단절 수정."
    },
    "ELSA-2026-50094": {
        "en": "Fixes two mptcp race conditions (CVE-2025-40257 in pm_del_add_timer, CVE-2025-40258 in schedule_work) causing kernel crash under MPTCP load. Fixes TLS socket dst lookup race (CVE-2025-40149) causing potential use-after-free in network stack.",
        "ko": "MPTCP 경로 관리자 타이머 삭제 중(CVE-2025-40257) 및 `mptcp_schedule_work()`(CVE-2025-40258) 경쟁 상태로 인한 커널 크래시 수정. TLS 소켓에서 목적지 경로(dst) 조회 중 경쟁 상태(CVE-2025-40149)로 발생하는 Use-After-Free 수정."
    },
    "RHSA-2026:2594": {
        "en": "Fixes RDMA/core slab-use-after-free in ib_register_device() (CVE-2025-38022) causing kernel crash on InfiniBand device registration. Fixes net/sched mqprio stack out-of-bounds write in tc entry parsing (CVE-2025-38568) enabling privilege escalation. Fixes Bluetooth MGMT out-of-bounds write (CVE-2025-38569) enabling privilege escalation.",
        "ko": "RDMA/core의 `ib_register_device()` slab-use-after-free(CVE-2025-38022)로 InfiniBand 장치 등록 시 커널 크래시 수정. net/sched mqprio tc 엔트리 파싱 스택 OOB 쓰기(CVE-2025-38568) 권한 상승 취약점 수정. Bluetooth MGMT OOB 쓰기 권한 상승 수정."
    },
    "USN-8052-1": {
        "en": "Addresses improper initialization of CPU cache memory allowing local attacker to overwrite SEV-SNP guest memory resulting in loss of data integrity (CVE-2024-36357, CVE-2024-36350).",
        "ko": "CPU 캐시 메모리 초기화 오류로 인한 SEV-SNP 게스트 메모리 덮어쓰기 및 데이터 무결성 손실(CVE-2024-36357, CVE-2024-36350) 취약점 완화."
    },
    "RHSA-2026:3124": {
        "en": "Fixes RDMA/core slab-use-after-free in ib_register_device (CVE-2025-38022), smb client use-after-free in cifs_fill_dirent (CVE-2025-38051), and mptcp schedule_work race condition (CVE-2025-40258) causing kernel crashes.",
        "ko": "RDMA/core `ib_register_device` slab-use-after-free(CVE-2025-38022), smb 클라이언트 UAF(CVE-2025-38051) 및 mptcp `mptcp_schedule_work()` 경쟁 상태(CVE-2025-40258)로 인한 커널 크래시 수정."
    },
    "USN-8043-1-24.04_LTS": {
        "en": "Resolves vulnerability in GnuTLS causing resource consumption and crashes, resulting in denial of service and potential arbitrary code execution (CVE-2025-9820, CVE-2025-14831).",
        "ko": "GnuTLS 내 자원 고갈 및 크래시를 유발하여 서비스 거부(DoS) 및 임의 코드 실행을 허용하는 취약점(CVE-2025-9820, CVE-2025-14831) 해결."
    },
    "RHSA-2026:2661": {
        "en": "Resolves Denial-of-Service in github.com/sirupsen/logrus due to large single-line payload parsing (CVE-2025-15284).",
        "ko": "github.com/sirupsen/logrus에서 대용량 단일 줄 페이로드 처리 시 발생하는 서비스 거부(DoS) 취약점(CVE-2025-15284) 수정."
    },
    "RHSA-2026:2786": {
        "en": "Fixes integer overflow in memalign causing heap corruption (CVE-2026-0861) and wordexp uninitialized memory return (CVE-2025-15281) in glibc.",
        "ko": "glibc에서 힙 메모리 손상을 유발하는 memalign 정수 오버플로우(CVE-2026-0861) 및 wordexp 초기화되지 않은 메모리 반환(CVE-2025-15281) 수정."
    },
    "RHSA-2026:2484": {
        "en": "Resolves pyasn1 Denial of Service due to memory exhaustion from malformed RELATIVE-OID (CVE-2026-23490) and Tornado Quadratic DoS via Repeated Header Coalescing (CVE-2025-67725).",
        "ko": "잘못된 RELATIVE-OID로 인한 pyasn1 메모리 고갈 서비스 거부(CVE-2026-23490) 및 Tornado 헤더 병합 시 발생하는 2차 DoS(CVE-2025-67725) 취약점 수정."
    },
    "RHSA-2026:3122": {
        "en": "Fixes containerd local privilege escalation (CVE-2024-25621) and SSH client panic due to unexpected SSH_AGENT_SUCCESS (CVE-2025-47913).",
        "ko": "containerd 로컬 권한 상승(CVE-2024-25621) 및 예기치 않은 SSH_AGENT_SUCCESS로 인한 SSH 클라이언트 패닉(CVE-2025-47913) 취약점 수정."
    },
    "RHSA-2026:2309": {
        "en": "Resolves urllib3 unbounded decompression chain leading to resource exhaustion (CVE-2025-66418) and pyasn1 memory exhaustion DoS (CVE-2026-23490).",
        "ko": "urllib3 무제한 압축 해제 체인으로 인한 자원 고갈(CVE-2025-66418) 및 pyasn1 메모리 고갈 DoS(CVE-2026-23490) 취약점 해결."
    },
    "ELSA-2026-50113": {
        "en": "Fixes tipc_mon_reinit_self() Use-After-Free (CVE-2025-40280) and fuse readahead reclaim deadlock (CVE-2025-68821). Resolves vsock connect() signal handling race (CVE-2025-40248) preventing kernel crashes.",
        "ko": "`tipc_mon_reinit_self()` Use-After-Free(CVE-2025-40280) 및 fuse 미리읽기 회수 교착 상태(CVE-2025-68821) 해결. 커널 크래시를 유발하는 vsock `connect()` 시그널 처리 경쟁 상태(CVE-2025-40248) 수정."
    },
    "USN-8005-1-24.04_LTS": {
        "en": "Fixes multiple glibc integer overflows in memalign (CVE-2026-0861) and uninitialized memory access in wordexp (CVE-2025-15281) preventing application crashes and memory corruption.",
        "ko": "애플리케이션 크래시 및 메모리 손상을 유발하는 memalign 정수 오버플로우(CVE-2026-0861) 및 wordexp 미초기화 메모리 접근(CVE-2025-15281) 등 glibc 취약점 수정."
    },
    "RHSA-2026:1541": {
        "en": "Resolves resource exhaustion via malformed DNSKEY handling (CVE-2025-8677) and BIND cache poisoning attacks with unsolicited RRs/weak PRNG (CVE-2025-40778, CVE-2025-40780).",
        "ko": "잘못된 DNSKEY 처리로 인한 자원 고갈(CVE-2025-8677) 및 의도치 않은 RR/약한 PRNG로 인한 BIND 캐시 포이즈닝 공격(CVE-2025-40778, CVE-2025-40780) 취약점 해결."
    },
    "RHSA-2026:3042": {
        "en": "Fixes arbitrary code execution due to out-of-bounds write in PKCS#12 processing (CVE-2025-69419) and RFC 3211 KEK Unwrap out-of-bounds access (CVE-2025-9230) in OpenSSL.",
        "ko": "OpenSSL PKCS#12 처리 중 발생하는 OOB 쓰기로 인한 임의 코드 실행(CVE-2025-69419) 및 RFC 3211 KEK Unwrap 범위 초과 접근(CVE-2025-9230) 취약점 수정."
    },
    "USN-7980-1-24.04_LTS": {
        "en": "Resolves arbitrary code execution and memory exhaustion vulnerabilities in OpenSSL processing affecting system stability under load (CVE-2025-69419).",
        "ko": "임의 코드 실행 및 메모리 고갈을 유발하는 OpenSSL 취약점(CVE-2025-69419)을 수정하여 시스템 안정성 및 서비스 거부(DoS) 문제 해결."
    },
    "USN-7866-1-24.04_LTS": {
        "en": "Fixes Intel Xeon 6 out-of-bounds writes in SGX/TDX memory subsystem (CVE-2025-24305) and active allocate resource management errors causing local denial of service (CVE-2025-20109).",
        "ko": "Intel SGX/TDX 사용 시 메모리 하위 시스템에서 발생하는 OOB 쓰기(CVE-2025-24305) 및 리소스 할당 오류로 인한 시스템 크래시/DoS(CVE-2025-20109) 마이크로코드 취약점 해결."
    },
    "USN-8056-1-24.04_LTS": {
        "en": "Fixes U-Boot vulnerabilities involving improper handling of DHCP responses (CVE-2024-57258) preventing potential boot failures and compromise.",
        "ko": "DHCP 응답의 잘못된 처리로 인해 발생하는 U-Boot 취약점(CVE-2024-57258)을 수정하여 잠재적 부팅 실패 및 보안 손상 방지."
    },
    "USN-8049-1-24.04_LTS": {
        "en": "Resolves QEMU vulnerability (CVE-2026-24708) mitigating hypervisor escapes and system crashes.",
        "ko": "하이퍼바이저 탈출 및 시스템 크래시를 방지하기 위해 QEMU 보안 취약점(CVE-2026-24708) 수정."
    },
    "USN-7047-1-24.04_LTS": {
        "en": "Fixes memory exhaustion bugs in libvirt (CVE-2025-13193) leading to denial of service for managed virtual machines.",
        "ko": "libvirt에서 가상 머신의 서비스 거부(DoS)를 유발할 수 있는 메모리 고갈 취약점(CVE-2025-13193, CVE-2025-12748) 해결."
    },
    "USN-7983-1-24.04_LTS": {
        "en": "Resolves Docker vulnerability (CVE-2025-64329) and containerd local privilege escalation (CVE-2024-25621) preventing denial of service and host compromise.",
        "ko": "Docker/containerd 환경에서 로컬 권한 상승(CVE-2024-25621) 및 서비스 거부(DoS) 취약점(CVE-2025-64329) 방지."
    },
    "RHSA-2026:1540": {
        "en": "Fixes runc container escape via masked path mount race conditions (CVE-2025-31133) and arbitrary procfs write redirects causing denial of service (CVE-2025-52881).",
        "ko": "runc의 마운트 경쟁 상태를 악용한 컨텍스트 탈출(CVE-2025-31133) 및 임의 procfs 쓰기 리디렉션으로 인한 서비스 거부 및 보안 탈출(CVE-2025-52881) 취약점 수정."
    },
    "ELSA-2025-28040": {
        "en": "Resolves double free in drm_sched_job_add_resv_dependencies (CVE-2025-40096) and cifs_sb_tlink refcount leak (CVE-2025-40103) causing kernel instability. Fixes incorrect pkt_len handling in ice_vc_fdir_parse_raw() (CVE-2025-22117).",
        "ko": "커널 불안정성을 유발하는 `drm_sched_job` 이중 해제(CVE-2025-40096) 및 `cifs_sb_tlink` 역참조 누수(CVE-2025-40103) 해결. `ice` 드라이버의 패킷 처리 오류(CVE-2025-22117) 보완."
    }
}

def process_review():
    print(f"Loading {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found in {os.getcwd()}")
        return

    final_rows = []
    
    for item in data:
        # Lead item represents the "Latest" physical update.
        lead_impacts = is_critical(item['full_text'] + " " + item['summary'] + " " + item.get('diff_content', ''))
        
        candidates = []
        # Add Lead
        candidates.append({
            'id': item['id'],
            'date': item['date'],
            'version': item.get('specific_version', item['component']),
            'impacts': lead_impacts,
            'is_critical': len(lead_impacts) > 0,
            'obj': item,
            'full_text': item['full_text'] + " " + item['summary']
        })
        
        # Add History
        for hist in item.get('history', []):
            h_text = hist.get('diff_summary', '')
            h_impacts = is_critical(h_text)
            candidates.append({
                'id': hist['id'],
                'date': hist['date'],
                'version': item.get('specific_version', item['component']) + " (Old)",
                'impacts': h_impacts,
                'is_critical': len(h_impacts) > 0,
                'obj': hist,
                'full_text': h_text
            })
            
        # Candidates are roughly sorted by date descending (Lead is newest).
        # Strategy: Iterate from top. Find first CRITICAL item.
        
        selected_cand = None
        selected_idx = -1
        
        for i, cand in enumerate(candidates):
            if cand['is_critical']:
                selected_cand = cand
                selected_idx = i
                break
        
        if not selected_cand:
            # No critical version found in this group. Skip.
            print(f"Skipping {item['component']} ({item['id']}): No critical impact found.")
            # Depending on business rule, we might keep it if it fixes *something*, but SKILL says "Criteria for Inclusion".
            continue
            
        # If we selected Index 2 (older), we ignore Index 0 and 1.
        # We aggregate descriptions from Index 2 downwards (if they are also critical).
        
        critical_subset = [c for c in candidates[selected_idx:] if c['is_critical']]
        
        # Aggregate logic
        agg_impacts = set()
        agg_sentences = []
        
        for c in critical_subset:
            agg_impacts.update(c['impacts'])
            sents = extract_key_sentence(c['full_text'])
            agg_sentences.extend(sents)
            
        # De-dupe sentences
        unique_sentences = list(dict.fromkeys(agg_sentences))
        
        # Count for "Cumulative" tag
        is_cumulative = len(critical_subset) > 1
        
        # Generate Descriptions
        # Note: history_count is purely for the tag "(누적 패치 포함: N건)"
        history_count = len(critical_subset)
        
        ko_desc = BEST_PRACTICE_DESCS.get(selected_cand['id'], {}).get("ko")
        en_desc = BEST_PRACTICE_DESCS.get(selected_cand['id'], {}).get("en")
        
        if not ko_desc:
            ko_desc = generate_korean_desc(selected_cand['id'], list(agg_impacts), is_cumulative, history_count)
        if not en_desc:
            en_desc = generate_english_desc(selected_cand['id'], list(agg_impacts), is_cumulative)
        
        row = {
            "Issue ID": selected_cand['id'],
            "Vendor": item['vendor'],
            "Dist Version": item.get('dist_version', ''),
            "Component": item['component'],
            "Version": item.get('specific_version', ''),
            "Date": selected_cand['date'],
            "Criticality": "Critical",
            "Patch Description": en_desc,
            "한글 설명": ko_desc,
            "Reference": item.get('ref_url', '')
        }
        final_rows.append(row)
        print(f"Added {selected_cand['id']} ({item['component']}) - Critical: {list(agg_impacts)}")

    # Write CSV
    with open(OUTPUT_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ["Issue ID", "Vendor", "Dist Version", "Component", "Version", "Date", "Criticality", "Patch Description", "한글 설명", "Reference"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)
        
    print(f"Generated {OUTPUT_FILE} with {len(final_rows)} rows.")

if __name__ == "__main__":
    process_review()
