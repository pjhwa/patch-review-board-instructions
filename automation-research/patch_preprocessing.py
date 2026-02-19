import re
import csv
import os
import json
from datetime import datetime
import glob

# NOTE: This script replaces 'perform_llm_review_simulation.py'. 
# It does NOT perform the review. It performs the mechanical PRE-PROCESSING 
# (Collection, Pruning, Aggregation) to prepare a clean dataset for the AI Agent (LLM) to review.

# INPUT_FILE = "patch_review_summary.md" # Source data (aggregated from RSS/Web)
JSON_DIR = r"batch_data"
OUTPUT_FILE = "patches_for_llm_review.json"

# --- CONFIGURATION: PRUNING RULES ---

# STRICT WHITELIST: ONLY components capable of causing "System Critical" failures.
# Criteria: Hang/Crash, Data Loss, Failover Failure, Hardware Malfunction, Critical Security.

SYSTEM_CORE_COMPONENTS = [
    # 1. Kernel & Hardware Interaction (Hang, Crash, Panic risk)
    "kernel", "linux-image", "microcode", "linux-firmware", 
    "shim", "grub", "grub2", "efibootmgr", "mokutil", # Boot critical
    
    # 2. Storage & Filesystem (Data Loss, Corruption risk)
    "lvm2", "device-mapper", "multipath-tools", "kpartx", 
    "e2fsprogs", "xfsprogs", "dosfstools", "nfs-utils", "cifs-utils",
    "iscsi-initiator-utils", "open-iscsi", "smartmontools",
    
    # 3. Cluster & High Availability (Failover Failure risk)
    "pacemaker", "corosync", "pcs", "fence-agents", "resource-agents", "keepalived",
    
    # 4. Critical Networking (Connectivity Loss risk)
    "networkmanager", "firewalld", "iptables", "nftables", 
    "bind", "bind-utils", # DNS failure = Service outage
    "dhcp", "dhclient",
    
    # 5. Core System Services (System Hang/Unavailability risk)
    "systemd", "udev", "initscripts", "glibc", # Basic execution env
    "dbus", "audit", # Security audit / IPC
    
    # 6. Critical Security (Remote Compromise risk)
    "openssl", "gnutls", "nss", "ca-certificates",
    "openssh", "sshd", "sudo", "pam", "polkit",
    "selinux-policy", "libselinux",
    
    # 7. Virtualization Infrastructure (Host Crash risk)
    "libvirt", "qemu-kvm", "qemu", "kvm",
    "docker", "podman", "runc", "containerd", "kubernetes", "kubelet"
]

# REMOVED from previous broad list:
# - bash, coreutils, sed, awk, grep: Bugs here rarely cause System Hang/Crash (usually just script error).
# - python, ruby, perl, php: Runtimes, not system core.
# - gtk, gnome, X11: GUI not critical for server stability.

# Blacklist (Redundant but safety net)
EXCLUDED_PACKAGES_EXPLICIT = [
    "firefox", "thunderbird", "libreoffice", "evolution", 
    "gimp", "inkscape", "cups", "avahi", "bluez", "pulseaudio", "pipewire",
    "gnome", "kde", "xorg", "wayland", "mesa", "webkit",
    "python-urllib3", "python-requests", "nodejs", "ruby", "perl", "php",
    "tar", "gzip", "zip", "unzip", "vim", "nano", "emacs", # Editors/Tools
    "compiz", "alsa", "sound"
]

def get_component_name(vendor, title, summary):
    text = (title + " " + summary).lower()
    
    # 1. Oracle Special Case: UEK
    if vendor == "Oracle":
        if "uek" in text or "unbreakable enterprise kernel" in text:
            return "kernel-uek"
        return "other" # Will be filtered out

    # 2. Ubuntu/RHEL Heuristics
    # Check for direct matches in whitelist first
    for core in SYSTEM_CORE_COMPONENTS:
        # Regex word boundary check for accuracy (avoid 'lib' matching 'glib')
        if re.search(fr'\b{re.escape(core)}\b', text):
            return core
            
    # 3. Regex fallback <name>-<version>
    m = re.search(r'([a-z0-9]+(-[a-z0-9]+)*)-\d+\.\d+', text)
    if m: 
        name = m.group(1)
        # Verify if extracted name partial matches core list (so we don't return 'firefox')
        for core in SYSTEM_CORE_COMPONENTS:
            if core == name or (name.startswith(core + "-")):
                return core
        return name
        
    return "other"

def is_system_critical(vendor, component, text):
    comp = component.lower()
    txt = text.lower()
    
    # --- RULE 1: ORACLE LINUX IS "UEK ONLY" ---
    if vendor == "Oracle":
        if "kernel-uek" in comp: return True
        # Allow variations like 'Unbreakable Enterprise Kernel'
        if "unbreakable enterprise kernel" in txt and "kernel" in comp: return True
        return False

    # --- RULE 2: STRICT WHITELIST (NARROWED) ---
    
    # 2.1 First, Check Blacklist for explicit exclusion (Safety Net)
    for bad in EXCLUDED_PACKAGES_EXPLICIT:
        if bad == comp or (f"{bad}-" in comp): return False

    # 2.2 Verify against Whitelist
    for core in SYSTEM_CORE_COMPONENTS:
        # Exact match or prefix match (e.g. 'kernel' matches 'kernel-header')
        if core == comp: return True
        if comp.startswith(f"{core}-"): return True
        
        # Text based match (fallback if component detection failed but text is clear)
        if f"package {core}" in txt or f"{core} package" in txt:
            return True

    # 2.3 Special Case: 'Kernel' keyword
    if "kernel" in comp and "texlive" not in comp: # texlive-kernel is a doc package
        return True
        
    # If not in whitelist -> PRUNE
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
            date_str = data.get('pubDate', data.get('dateStr', ''))
            if date_str: date_str = date_str[:10]  # First 10 chars (YYYY-MM-DD or similar) -> simplistic
            
            title = data.get('title', '')
            summary = data.get('synopsis', '')
            full_text = data.get('full_text', '') + " " + title + " " + summary
            
            component = get_component_name(vendor, title, summary)
            
            raw_list.append({
                'id': patch_id,
                'vendor': vendor,
                'date': date_str,
                'component': component,
                'summary': summary,
                'full_text': full_text,
                'ref_url': data.get('url', '')
            })

        except Exception as e:
            print(f"Error reading {json_path}: {e}")

    print(f"Raw Patches: {len(raw_list)}")

    # --- Step 2: Pruning ---
    pruned_list = []
    for p in raw_list:
        text = p['full_text'].lower()
        
        # Red Hat Specific Exclusions (Product filtering)
        if p['vendor'] == "Red Hat":
            if "update services for sap" in text: continue
            if "aus" in text or "eus" in text: continue
            if "kernel-rt" in text: continue
            if "rhui" in text or "update infrastructure" in text: continue
            if "openshift" in text or "openstack" in text: continue
            
        # Criticality Check (Strict Whitelist + Oracle Rule)
        if not is_system_critical(p['vendor'], p['component'], text):
            # print(f"Pruned: {p['vendor']} {p['component']} ({p['id']})")
            continue
            
        pruned_list.append(p)
        
    print(f"Pruned Candidates: {len(pruned_list)}")

    # --- Step 4 (Prep): Aggregation ---
    # Group by Vendor + Component to prepare for LLM Review
    grouped = {}
    for p in pruned_list:
        # Use simple component name for grouping (e.g. 'kernel-uek' or 'bind')
        # We need to normalize component names further for aggregation if needed
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
                'summary': old['summary'][:200] + "..." # Truncate for token efficiency
            })
            
        latest['history'] = history_context
        # Contextual Instructions based on Vendor
        review_note = ""
        if latest['vendor'] == "Oracle": review_note = "Only verify this is UEK kernel."
        
        latest['review_instructions'] = f"Analyze this '{latest['component']}' patch ({review_note}). Check for System Hang, Data Loss, Boot Fail, or Critical Security. Ignore minor bugs. Merge insights from {len(history_context)} previous patches if they are relevant."
        
        final_candidates.append(latest)
        
    print(f"Final Candidates for LLM: {len(final_candidates)}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_candidates, f, indent=2, ensure_ascii=False)
        
    print(f"Saved review packet to {OUTPUT_FILE}")

if __name__ == "__main__":
    preprocess_patches()
