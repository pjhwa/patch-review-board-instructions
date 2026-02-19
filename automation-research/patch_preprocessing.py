import re
import csv
import os
import json
from datetime import datetime
import glob

# NOTE: This script replaces 'perform_llm_review_simulation.py'. 
# It does NOT perform the review. It performs the mechanical PRE-PROCESSING 
# (Collection, Pruning, Aggregation) to prepare a clean dataset for the AI Agent (LLM) to review.

JSON_DIR = r"batch_data"
OUTPUT_FILE = "patches_for_llm_review.json"

# --- CONFIGURATION: PRUNING RULES ---
# STRICT WHITELIST: ONLY components capable of causing "System Critical" failures.
SYSTEM_CORE_COMPONENTS = [
    # 1. Kernel & Hardware Interaction
    "kernel", "linux-image", "microcode", "linux-firmware", 
    "shim", "grub", "grub2", "efibootmgr", "mokutil",
    
    # 2. Storage & Filesystem
    "lvm2", "device-mapper", "multipath-tools", "kpartx", 
    "e2fsprogs", "xfsprogs", "dosfstools", "nfs-utils", "cifs-utils",
    "iscsi-initiator-utils", "open-iscsi", "smartmontools",
    
    # 3. Cluster & High Availability
    "pacemaker", "corosync", "pcs", "fence-agents", "resource-agents", "keepalived",
    
    # 4. Critical Networking
    "networkmanager", "firewalld", "iptables", "nftables", 
    "bind", "bind-utils", "dhcp", "dhclient",
    
    # 5. Core System Services
    "systemd", "udev", "initscripts", "glibc", 
    "dbus", "audit",
    
    # 6. Critical Security
    "openssl", "gnutls", "nss", "ca-certificates",
    "openssh", "sshd", "sudo", "pam", "polkit",
    "selinux-policy", "libselinux",
    
    # 7. Virtualization Infrastructure
    "libvirt", "qemu-kvm", "qemu", "kvm",
    "docker", "podman", "runc", "containerd", "kubernetes", "kubelet"
]

# Ubuntu LTS versions whose Standard Security Maintenance has EXPIRED (as of 2026-02-19).
# Reference: https://ubuntu.com/about/release-cycle
# 14.04 LTS: expired 2019-04 | 16.04 LTS: expired 2021-04 | 18.04 LTS: expired 2023-04 | 20.04 LTS: expired 2025-05
UBUNTU_EOL_LTS_VERSIONS = {"14.04 LTS", "16.04 LTS", "18.04 LTS", "20.04 LTS"}

EXCLUDED_PACKAGES_EXPLICIT = [
    "firefox", "thunderbird", "libreoffice", "evolution", 
    "gimp", "inkscape", "cups", "avahi", "bluez", "pulseaudio", "pipewire",
    "gnome", "kde", "xorg", "wayland", "mesa", "webkit",
    "python-urllib3", "python-requests", "nodejs", "ruby", "perl", "php",
    "tar", "gzip", "zip", "unzip", "vim", "nano", "emacs",
    "compiz", "alsa", "sound"
]

def parse_date(date_str):
    """Normalizes date string to YYYY-MM-DD or YYYY-MM"""
    if not date_str: return "Unknown"
    date_str = date_str.strip()
    
    # Format: "2026-February" -> "2026-02"
    match = re.match(r"(\d{4})-(January|February|March|April|May|June|July|August|September|October|November|December)", date_str, re.IGNORECASE)
    if match:
        year = match.group(1)
        month_name = match.group(2)
        try:
            dt = datetime.strptime(month_name, "%B")
            return f"{year}-{dt.month:02d}"
        except: pass

    # Format: "Thu, 12 Feb 2026..."
    try:
        # Simple extraction of YYYY-MM-DD if ISO format exists
        if "T" in date_str: return date_str[:10]
        # Or simplistic parse if standard format failed
    except: pass
    
    return date_str[:10] # Fallback

def extract_oracle_version(text):
    """Extracts Oracle Linux version (6, 7, 8, 9, 10) from text"""
    # 1. Explicit "Oracle Linux X"
    match = re.search(r"Oracle Linux (\d+)", text, re.IGNORECASE)
    if match: return f"ol{match.group(1)}"
    
    # 2. Rpm tags like "el9", "el10", "el8" in filenames
    match_el = re.search(r"\.el(\d+)uek", text, re.IGNORECASE)
    if match_el: return f"ol{match_el.group(1)}"
    
    # 3. Simple text indicators
    if "el8" in text.lower(): return "ol8"
    if "el9" in text.lower(): return "ol9"
    if "el7" in text.lower(): return "ol7"
    if "el10" in text.lower() or "ol10" in text.lower(): return "ol10"
    
    return ""

def extract_redhat_date(text):
    """Extracts 'Issued: YYYY-MM-DD' from Red Hat full text"""
    # Try English "Issued: YYYY-MM-DD"
    match = re.search(r"Issued:\s*(\d{4}-\d{2}-\d{2})", text)
    if match: return match.group(1)

    # Try Japanese "発行日: YYYY-MM-DD"
    match = re.search(r"発行日:\s*(\d{4}-\d{2}-\d{2})", text)
    if match: return match.group(1)
    
    return ""

def extract_redhat_dist_version(full_text):
    """Extracts RHEL major version numbers from Red Hat advisory text.
    
    Strategy:
    1. Parse 'Affected Products' section for lines like:
       'Red Hat Enterprise Linux for x86_64 - Update Services for SAP Solutions 9.2 x86_64'
       -> extracts '9'
    2. Fallback: scan full_text for 'Red Hat Enterprise Linux X' patterns.
    
    Returns a sorted list of unique major version strings e.g. ['8', '9'].
    Returns ['Unknown'] if nothing is found.
    """
    versions = set()

    # Strategy 1: Parse 'Affected Products' section
    # Look for section header and extract lines until next section
    affected_match = re.search(
        r"Affected Products[:\s]*(.+?)(?=\n(?:[A-Z][A-Za-z ]+:|Fixes|References|Packages|$))",
        full_text, re.DOTALL | re.IGNORECASE
    )
    if affected_match:
        affected_block = affected_match.group(1)
        # Match 'Red Hat Enterprise Linux ... X.Y ...' or 'Red Hat Enterprise Linux X'
        for m in re.finditer(
            r"Red Hat Enterprise Linux[^\n]*?\b(\d+)(?:\.\d+)?\b",
            affected_block, re.IGNORECASE
        ):
            versions.add(m.group(1))

    # Strategy 2: Fallback — scan full text
    if not versions:
        for m in re.finditer(r"Red Hat Enterprise Linux (\d+)", full_text, re.IGNORECASE):
            versions.add(m.group(1))

    if versions:
        return sorted(versions)
    return ["Unknown"]

def extract_redhat_content(text):
    """Clean Red Hat boilerplate and extract Description/Topic/Fixes"""
    # 1. Remove Top Boilerplate (Cookie Warning & Nav)
    # The text often starts with <div id="noJavaScript"... or "Skip to..."
    # We look for the Advisory Header "RHSA-..." or "RHBA-..."
    
    header_match = re.search(r"(RH[SBE]A-\d{4}:\d+ - Security Advisory|RH[SBE]A-\d{4}:\d+ - Bug Fix Advisory)", text)
    start_idx = 0
    if header_match:
        start_idx = header_match.start()
        
    cleaned_text = text[start_idx:]
    
    # 2. Extract Key Sections (Description, Topic, Security Fixes)
    # We want to capture from "Description" or "Topic" until "Solution" or "References"
    
    content = ""
    
    # Try finding sections
    # Note: Case sensitive or insensitive depending on consistency. The JSON suggests "Description" and "Topic" are Capitalized.
    
    # Priority 1: Description
    desc_match = re.search(r"\bDescription\b", cleaned_text)
    topic_match = re.search(r"\bTopic\b", cleaned_text)
    
    extraction_start = -1
    if desc_match:
        extraction_start = desc_match.start()
    elif topic_match:
        extraction_start = topic_match.start()
        
    if extraction_start != -1:
        # Find end marker
        sol_match = re.search(r"\bSolution\b", cleaned_text[extraction_start:])
        ref_match = re.search(r"\bReferences\b", cleaned_text[extraction_start:])
        
        extraction_end = len(cleaned_text)
        if sol_match:
            extraction_end = extraction_start + sol_match.start()
        elif ref_match:
            extraction_end = extraction_start + ref_match.start()
            
        return cleaned_text[extraction_start:extraction_end].strip()
        
    # Fallback: Just return cleaned text (post-header) truncated
    return cleaned_text[:1000]

def extract_diff_content(text, vendor):
    """Extracts relevant 'diff' content (changes) from full text"""
    lower_text = text.lower()
    
    if vendor == "Oracle":
        # Extract "Description of changes" section
        marker = "description of changes:"
        idx = lower_text.find(marker)
        if idx != -1:
            return text[idx+len(marker):].strip()
            
    elif vendor == "Ubuntu":
        # Extract "Details" section
        marker = "details"
        idx = lower_text.find(marker)
        if idx != -1:
            # Try to stop at next section (e.g. "Update instructions")
            end_marker = "update instructions"
            end_idx = lower_text.find(end_marker)
            if end_idx != -1:
                return text[idx+len(marker):end_idx].strip()
            return text[idx+len(marker):].strip()

    elif vendor == "Red Hat":
        return extract_redhat_content(text)
            
    # Default: Return cleanedsummary/synopsis
    return text[:500] + "..." if len(text) > 500 else text

def get_component_name(vendor, title, summary, full_text):
    text = (title + " " + summary + " " + full_text).lower()
    
    # 1. Oracle Special Case: UEK + Versioning
    if vendor == "Oracle":
        if "uek" in text or "unbreakable enterprise kernel" in text:
            comp = "kernel-uek"
            
            # Extract Major.Minor version for stream splitting (e.g. 5.15, 6.12)
            version_match = re.search(r'(\d+\.\d+)\.\d+', text)
            kern_series = f"-v{version_match.group(1)}" if version_match else ""
            
            ol_ver = extract_oracle_version(text)
            ver_suffix = f"-{ol_ver}" if ol_ver else ""
            
            return f"{comp}{kern_series}{ver_suffix}"
        return "other"
    
    # 2. Ubuntu/RHEL Heuristics
    for core in SYSTEM_CORE_COMPONENTS:
        if re.search(fr'\b{re.escape(core)}\b', text):
            return core
            
    m = re.search(r'([a-z0-9]+(-[a-z0-9]+)*)-\d+\.\d+', text)
    if m: 
        name = m.group(1)
        for core in SYSTEM_CORE_COMPONENTS:
            if core == name or (name.startswith(core + "-")):
                return core
        return name
        
    return "other"

def extract_specific_version(text, component, patch_id=None):
    """Extracts exact version number if possible (e.g. 5.4.17-...)"""
    # User Overrides & Manual Lookups
    overrides = {
        "RHSA-2026:1815": "openssh-8.7p1-30.el9_2.9",
        "RHSA-2026:2594": "kernel-5.14.0-427.110.1.el9_4", # Src RPM
        "RHSA-2026:2486": "fence-agents-4.2.1-89.el8_6.21", 
        "RHSA-2026:1733": "openssl-3.0.1-46.el9_0.7", # Minimum version
        "RHSA-2026:2484": "pcs-0.10.11", # Advisory updates 'pcs', specific version varies, using generic base
        "RHSA-2026:2572": "rhacm-2.14-images", # Container images, no single RPM
        "RHSA-2026:2520": "toolbox-0.0.99.5.1-2.el9_4"
    }
    
    if patch_id in overrides:
        return overrides[patch_id]

    # Heuristic for kernel versions
    if "kernel" in component:
        m = re.search(r'(\d+\.\d+\.\d+-\d+(\.\d+)*(\.el\d+uek)?)', text)
        if m: return m.group(1)
    return ""

def is_system_critical(vendor, component, text):
    comp = component.lower()
    # Rule 1: Oracle UEK Only
    if vendor == "Oracle":
        return "kernel-uek" in comp
    
    # Rule 2: Strict Whitelist (RHEL/Ubuntu)
    for bad in EXCLUDED_PACKAGES_EXPLICIT:
        if bad == comp or (f"{bad}-" in comp): return False

    for core in SYSTEM_CORE_COMPONENTS:
        if core == comp: return True
        if comp.startswith(f"{core}-"): return True
        if f"package {core}" in text.lower(): return True

    if "kernel" in comp and "texlive" not in comp: return True
    return False

def preprocess_patches():
    print(f"Loading data from {JSON_DIR}...")
    
    raw_list = []
    
    # --- Step 1: Ingest JSONs directly ---
    json_files = glob.glob(os.path.join(JSON_DIR, "*.json"))
    print(f"Found {len(json_files)} JSON files.")

    for json_path in json_files:
        try:
            with open(json_path, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
                
            vendor = data.get('vendor', 'Unknown')
            patch_id = data.get('id', os.path.basename(json_path).replace('.json', ''))
            
            # Normalization
            date_raw = data.get('pubDate', data.get('dateStr', ''))
            date_str = parse_date(date_raw)
            
            title = data.get('title', '')
            summary = data.get('synopsis', '')
            full_text = data.get('full_text', '') 
            
            # Content Cleaning (Red Hat)
            if vendor == "Red Hat":
                rh_date = extract_redhat_date(full_text)
                full_text = extract_redhat_content(full_text)
                if rh_date: date_str = rh_date
                if not summary:
                    summary = title # Fallback
                
            # --- EXCLUSION FILTERS ---
            # 1. Garbage Data (Empty Content or Known Bad ID)
            if (len(full_text) < 50 and vendor == "Red Hat") or patch_id == "RHSA-2026:2664":
                continue
            
            # Exclude OpenShift product advisories (not RHEL core packages).
            # Check title/synopsis AND full_text to catch cases where OCP advisories
            # do not mention 'OpenShift' in title but affect only OCP products.
            if "openshift" in title.lower() or "openshift" in summary.lower():
                continue
            # Additional check: if 'Affected Products' only lists OCP (no RHEL line)
            if vendor == "Red Hat":
                affected_match = re.search(
                    r"Affected Products[:\s]*(.+?)(?=\n[A-Z]|$)", full_text, re.DOTALL | re.IGNORECASE
                )
                if affected_match:
                    ap_block = affected_match.group(1)
                    has_rhel = bool(re.search(r"Red Hat Enterprise Linux", ap_block, re.IGNORECASE))
                    has_ocp_only = bool(re.search(r"OpenShift Container Platform", ap_block, re.IGNORECASE))
                    if has_ocp_only and not has_rhel:
                        continue  # OCP-only advisory — skip

            # 2. User Blacklist (SAP, kernel-rt)
            if "SAP" in title or "Update Services for SAP" in summary:
                continue
            if "real time" in title.lower() or "kernel-rt" in title.lower() or "kernel-rt" in summary.lower():
                continue
            
            component = get_component_name(vendor, title, summary, full_text)
            specific_ver = extract_specific_version(full_text, component, patch_id)
            
            # Extract diff content for history/summary
            diff_content = extract_diff_content(full_text, vendor)
            if not diff_content: diff_content = summary

            # --- DIST VERSION EXTRACTION & SPLITTING ---
            dist_versions = []
            if vendor == "Ubuntu":
                # Find all "XX.XX LTS" patterns and filter out EOL versions
                lts_matches = re.findall(r"(\d{2}\.\d{2} LTS)", full_text + " " + title)
                if lts_matches:
                    active_lts = [v for v in sorted(set(lts_matches)) if v not in UBUNTU_EOL_LTS_VERSIONS]
                    dist_versions = active_lts
                # Non-LTS versions (25.10, etc.) are intentionally NOT included (not supported)
            
            elif vendor == "Oracle":
                # Extracted in get_component_name, but let's formalize here
                ol_ver = extract_oracle_version(full_text + " " + title) # e.g. "ol9"
                if ol_ver:
                    dist_versions = [ol_ver.replace("ol", "")] # "9"
            
            elif vendor == "Red Hat":
                # Use dedicated parser that checks 'Affected Products' section first
                dist_versions = extract_redhat_dist_version(full_text)
            
            if not dist_versions:
                dist_versions = ["Unknown"]

            # Log if we are splitting
            if len(dist_versions) > 1:
                print(f"Splitting {patch_id} into versions: {dist_versions}")

            for dist_ver in dist_versions:
                # Create a specific ID for this split if multiple
                unique_id = patch_id
                if len(dist_versions) > 1:
                    unique_id = f"{patch_id}-{dist_ver.replace(' ','_')}"
                
                # Re-extract component/version specific to this dist_ver context if possible
                # (For now, we use the global extraction but hint the Agent)
                
                # Attempt to extract detection specific to this Dist Version if provided
                target_specific_ver = specific_ver
                
                if vendor == "Ubuntu":
                   # Try to find the table row: "24.04 LTS noble runc – 1.3.3-..."
                   # Regex look for: {dist_ver} ... {component} – {version}
                   # escape dots in dist_ver
                   safe_ver = re.escape(dist_ver)
                   # Matches line like: "24.04 LTS noble runc – 1.3.3..."
                   row_match = re.search(fr"{safe_ver}.*?{component}\s+[–-]\s+([^\s]+)", full_text, re.IGNORECASE)
                   if row_match:
                       target_specific_ver = row_match.group(1)

                raw_list.append({
                    'id': unique_id,
                    'original_id': patch_id,
                    'vendor': vendor,
                    'dist_version': dist_ver,
                    'date': date_str,
                    'component': component,
                    'specific_version': target_specific_ver,
                    'summary': summary,
                    'diff_content': diff_content, 
                    'full_text': full_text + " " + title,
                    'ref_url': data.get('url', '')
                })

        except Exception as e:
            print(f"Error reading {json_path}: {e}")

    print(f"Raw Patches: {len(raw_list)}")

    # --- Step 2: Pruning ---
    pruned_list = []
    for p in raw_list:
        if not is_system_critical(p['vendor'], p['component'], p['full_text']):
            continue
        pruned_list.append(p)
        
    print(f"Pruned Candidates: {len(pruned_list)}")

    # --- Step 3: Aggregation ---
    grouped = {}
    for p in pruned_list:
        # Group by Vendor + Component (e.g. ('Oracle', 'kernel-uek-ol8'))
        key = (p['vendor'], p['component'])
        if key not in grouped: grouped[key] = []
        grouped[key].append(p)

    final_candidates = []
    
    for key, group in grouped.items():
        # Sort by ID descending (Latest first)
        group.sort(key=lambda x: x['id'], reverse=True)
        latest = group[0]
        
        # Prepare "History" context for the LLM
        history_context = []
        for old in group[1:]:
            history_context.append({
                'id': old['id'],
                'date': old['date'],
                'diff_summary': old['diff_content'][:800] # Provide diff content, truncated
            })
            
        latest['history'] = history_context
        
        review_note = ""
        if latest['vendor'] == "Oracle": 
            review_note = f"Verify this is UEK kernel ({latest['component']})."
        
        latest['review_instructions'] = f"Analyze this '{latest['component']}' patch ({review_note}). Check for System Hang, Data Loss, Boot Fail, or Critical Security. Merge insights from {len(history_context)} previous patches."
        latest['patch_name_suggestion'] = latest['specific_version'] if latest['specific_version'] else latest['component']
        
        final_candidates.append(latest)
        
    print(f"Final Candidates for LLM: {len(final_candidates)}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_candidates, f, indent=2, ensure_ascii=False)
        
    print(f"Saved review packet to {OUTPUT_FILE}")

if __name__ == "__main__":
    preprocess_patches()
