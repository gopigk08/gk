import urllib.request
import urllib.error
import re
import ssl
import sys
import time
import os

# ─── CONFIG ────────────────────────────────────────────────────────────
TEMPLATE_FILE = "template.m3u"
FRESH_JIO_URL = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
GK_URL        = "https://raw.githubusercontent.com/gopigk08/Omni/main/GK.m3u"
OUTPUT_FILE   = "omni.m3u"
RETRY_COUNT   = 3
RETRY_DELAY   = 5
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url, retries=RETRY_COUNT):
    print(f"  Fetching: {url[:90]}...")
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "sktechtv", "Accept": "*/*"})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                print(f"  ✅ OK — {len(data):,} bytes")
                return data
        except urllib.error.HTTPError as e:
            print(f"  ⚠️  HTTP {e.code} on attempt {attempt}/{retries}")
        except Exception as e:
            print(f"  ⚠️  Error on attempt {attempt}/{retries}: {e}")
        if attempt < retries:
            time.sleep(RETRY_DELAY)
    print(f"  ❌ All attempts failed.")
    return ""

def is_url_line(line):
    """True if line is a stream URL (not a comment/directive)."""
    s = line.strip()
    return bool(s) and not s.startswith("#") and (s.startswith("http") or s.startswith("rtmp"))

def extract_tvg_id_from_extinf(line):
    """Extract tvg-id from a #EXTINF line. Returns None if not found."""
    m = re.search(r'tvg-id="([^"]+)"', line)
    if m and m.group(1).strip():
        return m.group(1).strip()
    # Fallback: channel name after last comma
    parts = line.split(",")
    if len(parts) > 1:
        return parts[-1].strip()
    return None

def parse_template_ids(content):
    """
    Extract ordered list of tvg-ids from template.m3u.
    Template may have #KODIPROP, #EXTHTTP, etc. between EXTINF and URL.
    We only care about tvg-id order, not the actual URLs.
    """
    header = "#EXTM3U"
    ids = []
    for line in content.splitlines():
        line = line.strip()
        if re.match(r'#\s*EXTM3U', line, re.IGNORECASE):
            header = line
            continue
        if re.match(r'#\s*EXTINF', line, re.IGNORECASE):
            cid = extract_tvg_id_from_extinf(line)
            if cid:
                ids.append(cid)
    return header, ids

def parse_fresh_jio(content):
    """
    Parse fresh Jio M3U. Each channel block = one EXTINF line + one URL.
    Handles '# EXTINF' (with space) and '#EXTINF' (without space).
    Returns dict: tvg-id -> (extinf_line, url_line)
    """
    result = {}
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Match EXTINF line (with or without space after #)
        if re.match(r'#\s*EXTINF', line, re.IGNORECASE):
            extinf_line = line
            cid = extract_tvg_id_from_extinf(extinf_line)
            # Look ahead for the URL
            j = i + 1
            while j < len(lines) and not is_url_line(lines[j].strip()):
                j += 1
            if j < len(lines) and is_url_line(lines[j].strip()):
                url_line = lines[j].strip()
                if cid:
                    result[cid] = (extinf_line, url_line)
                i = j + 1
                continue
        i += 1
    return result

def parse_gk_m3u(content):
    """
    Parse GK.m3u into list of raw blocks (each block = list of lines).
    Preserves all lines as-is.
    """
    blocks = []
    current = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        # Skip the EXTM3U header line
        if re.match(r'#\s*EXTM3U', s, re.IGNORECASE):
            continue
        current.append(s)
        if is_url_line(s):
            if len(current) >= 2:
                blocks.append(current)
            current = []
    return blocks

def main():
    print("=" * 65)
    print("  OMNI M3U Generator")
    print("=" * 65)

    # ── 1. Read Template (for ordered channel IDs only) ──────────
    print(f"\n[1/4] Reading template: {TEMPLATE_FILE}")
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ '{TEMPLATE_FILE}' not found!")
        sys.exit(1)
    with open(TEMPLATE_FILE, "r", encoding="utf-8", errors="replace") as f:
        template_content = f.read()

    tmpl_header, tmpl_ids = parse_template_ids(template_content)
    print(f"  ✅ {len(tmpl_ids)} channel IDs extracted from template")
    print(f"  🔎 First 5 IDs: {tmpl_ids[:5]}")

    # ── 2. Fetch & Parse Fresh Jio TV ────────────────────────────
    print(f"\n[2/4] Fetching fresh Jio TV...")
    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        print("❌ Failed to fetch Jio TV. Aborting.")
        sys.exit(1)

    jio_dict = parse_fresh_jio(jio_content)
    print(f"  ✅ {len(jio_dict)} channels parsed from Jio TV")
    print(f"  🔎 First 5 Jio IDs: {list(jio_dict.keys())[:5]}")

    # ── 3. Match & Build Ordered Jio Channels ────────────────────
    print(f"\n[3/4] Matching template IDs → fresh Jio URLs...")
    matched_channels = []
    missing = []
    for cid in tmpl_ids:
        if cid in jio_dict:
            matched_channels.append((cid, jio_dict[cid]))
        else:
            missing.append(cid)

    print(f"  ✅ Matched : {len(matched_channels)} channels")
    if missing:
        print(f"  ⚠️  Missing : {len(missing)} channels")
        for m in missing[:10]:
            print(f"     - {m}")
        if len(missing) > 10:
            print(f"     ... and {len(missing)-10} more")

    # ── 4. Fetch GK.m3u ──────────────────────────────────────────
    print(f"\n[4/4] Fetching GK.m3u...")
    gk_content = fetch_url(GK_URL)
    gk_blocks = parse_gk_m3u(gk_content)
    print(f"  ✅ {len(gk_blocks)} channels from GK.m3u")

    # ── 5. Write omni.m3u ────────────────────────────────────────
    total = len(matched_channels) + len(gk_blocks)
    print(f"\n[5/5] Writing {total} channels → {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        # Write EXTM3U header
        f.write(tmpl_header + "\n")

        # Write matched Jio channels (fresh EXTINF + fresh URL — no stale cookies!)
        for cid, (extinf_line, url_line) in matched_channels:
            # Normalize: ensure EXTINF starts with '#EXTINF' (no space)
            normalized_extinf = re.sub(r'^#\s*EXTINF', '#EXTINF', extinf_line)
            f.write(normalized_extinf + "\n")
            f.write(url_line + "\n")

        # Write GK.m3u blocks as-is
        for block in gk_blocks:
            for line in block:
                f.write(line + "\n")

    print(f"  ✅ Written successfully!")
    print(f"\n✅ SUCCESS — omni.m3u ready with {total} channels!")
    print("=" * 65)

if __name__ == "__main__":
    main()
