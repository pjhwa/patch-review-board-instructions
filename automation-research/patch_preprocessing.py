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

def extract_specific_version(text, component):
    """Extracts exact version number if possible (e.g. 5.4.17-...)"""
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
            
            component = get_component_name(vendor, title, summary, full_text)
            specific_ver = extract_specific_version(full_text, component)
            
            # Extract diff content for history/summary
            diff_content = extract_diff_content(full_text, vendor)
            if not diff_content: diff_content = summary

            raw_list.append({
                'id': patch_id,
                'vendor': vendor,
                'date': date_str,
                'component': component,
                'specific_version': specific_ver,
                'summary': summary,
                'diff_content': diff_content, # Normalized content
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
