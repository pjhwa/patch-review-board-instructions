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

# Whitelist: ONLY these components are considered for the OS Patch Report.
# Everything else (Applications, Dev Tools, Libraries) is Pruned in Step 2.
SYSTEM_CORE_COMPONENTS = [
    "kernel", "glibc", "systemd", "udev", "grub", "dracut", "initscripts", 
    "openssh", "sshd", "sudo", "pam", "audit", "selinux", "firewalld", "iptables",
    "networkmanager", "dhcp", "bind", "dnsmasq", 
    "lvm", "multipath", "iscsi", "nfs", "cifs", "samba",
    "firmware", "microcode", "bios",
    "docker", "podman", "container-tools", "runc", "k8s", "kubelet",
    "libvirt", "qemu", "kvm",
    "bash", "shell", "coreutils", "util-linux",
    "openssl", "gnutls", "ca-certificates",
    "pcs", "pacemaker", "corosync", "fence"
]

# Blacklist: User-specific exclusions (Applications, GUI, etc.)
EXCLUDED_PACKAGES = [
    "python-urllib3", "thunderbird", "firefox", "libreoffice", "evolution", 
    "gimp", "inkscape", "cups", "avahi", "bluez", "pulseaudio", "pipewire",
    "gnome", "gtk", "qt", "xorg", "wayland", "mesa", "webkit",
    "flatpak", "snapd"
]

def get_component_name(vendor, title, summary):
    text = (title + " " + summary).lower()
    
    # 1. Check Keywords
    keywords = SYSTEM_CORE_COMPONENTS + ["python", "java", "ruby", "perl", "php"]
    for k in keywords:
        if re.search(fr'\b{re.escape(k)}\b', text):
            if k in ["java", "openjdk"]: return "java"
            return k
            
    # 2. Regex fallback <name>-<version>
    m = re.search(r'([a-z0-9]+(-[a-z0-9]+)*)-\d+\.\d+', text)
    if m: return m.group(1)
        
    return "other"

def is_system_critical(component, text):
    comp = component.lower()
    txt = text.lower()
    
    # 1. Blacklist
    for bad in EXCLUDED_PACKAGES:
        if bad in comp or bad in txt: return False
        
    # 2. Whitelist
    for core in SYSTEM_CORE_COMPONENTS:
        if core == comp or f"{core}-" in comp or f" {core} " in txt:
            return True
        # Loose match for kernel/firmware
    if "kernel" in comp or "boot" in comp: return True
        
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
        
        # Red Hat Specifics
        if p['vendor'] == "Red Hat":
            if "update services for sap" in text: continue
            if "aus" in text or "eus" in text: continue
            if "kernel-rt" in text: continue
            if "rhui" in text or "update infrastructure" in text: continue
            if "openshift" in text or "openstack" in text: continue
            
        # Criticality Check
        if not is_system_critical(p['component'], text):
            continue
            
        pruned_list.append(p)
        
    print(f"Pruned Candidates: {len(pruned_list)}")

    # --- Step 4 (Prep): Aggregation ---
    # Group by Vendor + Component to prepare for LLM Review
    grouped = {}
    for p in pruned_list:
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
        latest['review_instructions'] = f"Analyze this '{latest['component']}' patch. Check for System Hang, Data Loss, Boot Fail, or Critical Security (RCE/Root). Ignore minor bugs. Merge insights from {len(history_context)} previous patches if they are relevant impact-wise."
        
        final_candidates.append(latest)
        
    print(f"Final Candidates for LLM: {len(final_candidates)}")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_candidates, f, indent=2, ensure_ascii=False)
        
    print(f"Saved review packet to {OUTPUT_FILE}")

if __name__ == "__main__":
    preprocess_patches()
