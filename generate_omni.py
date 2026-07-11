import urllib.request
import urllib.error
import re
import ssl
import sys
import time
import os

# ─── CONFIG ─────────────────────────────────────────────────────────────
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
    """Fetch URL with retries. Returns decoded text, or empty string on failure."""
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
    print(f"  ❌ All {retries} attempts failed.")
    return ""

def get_channel_id(block_lines):
    """Extract tvg-id or fallback to channel name from an EXTINF block."""
    for line in block_lines:
        # Strip leading spaces and handle both '#EXTINF' and '# EXTINF' (space variant)
        stripped = line.lstrip()
        if re.match(r'#\s*EXTINF', stripped, re.IGNORECASE):
            m = re.search(r'tvg-id="([^"]+)"', stripped)
            if m and m.group(1).strip():
                return m.group(1).strip()
            # Fallback: channel name after last comma
            parts = stripped.split(",")
            if len(parts) > 1:
                return parts[-1].strip()
    return None

def is_url_line(line):
    """Return True if this line looks like a stream URL (not a comment)."""
    s = line.strip()
    return s and not s.startswith("#") and not s.startswith("//")

def parse_m3u(content):
    """
    Returns (header_line, list_of_blocks).
    Each block is a list of raw lines ending with a URL.
    Handles missing #EXTM3U header, '# EXTINF' variants, and blank lines.
    """
    lines = content.splitlines()

    # Find and extract the header line (may or may not be present)
    header = ""
    start = 0
    if lines and re.match(r'#\s*EXTM3U', lines[0].strip(), re.IGNORECASE):
        header = lines[0].strip()
        start = 1
    else:
        # No header found — use a default
        header = "#EXTM3U"

    blocks = []
    current = []
    for line in lines[start:]:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        current.append(line_stripped)
        if is_url_line(line_stripped):
            # URL line → block complete
            if len(current) >= 2:   # Must have at least one EXTINF + URL
                blocks.append(current)
            current = []

    return header, blocks

def main():
    print("=" * 62)
    print("  OMNI M3U Generator")
    print("=" * 62)

    # ── 1. Read Template ──────────────────────────────────────────
    print(f"\n[1/4] Reading template: {TEMPLATE_FILE}")
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ Template '{TEMPLATE_FILE}' not found!")
        print("   Upload your JIO TV playlist as 'template.m3u' in the repo root.")
        sys.exit(1)

    with open(TEMPLATE_FILE, "r", encoding="utf-8", errors="replace") as f:
        template_content = f.read()

    tmpl_header, tmpl_blocks = parse_m3u(template_content)
    tmpl_ids = [get_channel_id(b) for b in tmpl_blocks]
    tmpl_ids = [cid for cid in tmpl_ids if cid]  # Remove None
    print(f"  ✅ Template: {len(tmpl_blocks)} blocks, {len(tmpl_ids)} with valid IDs")

    # ── 2. Fetch Fresh Jio TV ────────────────────────────────────
    print(f"\n[2/4] Fetching fresh Jio TV playlist...")
    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        print("❌ Cannot fetch Jio TV. Aborting.")
        sys.exit(1)

    _, jio_blocks = parse_m3u(jio_content)
    jio_dict = {}
    for b in jio_blocks:
        cid = get_channel_id(b)
        if cid:
            jio_dict[cid] = b
    print(f"  ✅ Jio TV: {len(jio_blocks)} blocks, {len(jio_dict)} with valid IDs")

    # Debug: print first few IDs from Jio and template to verify matching
    print(f"  🔎 Sample Jio IDs   : {list(jio_dict.keys())[:5]}")
    print(f"  🔎 Sample tmpl IDs  : {tmpl_ids[:5]}")

    # ── 3. Match Template → Fresh ────────────────────────────────
    print(f"\n[3/4] Matching channels...")
    ordered_jio = []
    missing = []
    for cid in tmpl_ids:
        if cid in jio_dict:
            ordered_jio.append(jio_dict[cid])
        else:
            missing.append(cid)

    print(f"  ✅ Matched : {len(ordered_jio)}")
    if missing:
        print(f"  ⚠️  Missing : {len(missing)}")
        for m in missing[:10]:
            print(f"     - {m}")
        if len(missing) > 10:
            print(f"     ... and {len(missing)-10} more")

    # ── 4. Fetch GK.m3u ──────────────────────────────────────────
    print(f"\n[4/4] Fetching GK.m3u...")
    gk_content = fetch_url(GK_URL)
    _, gk_blocks = parse_m3u(gk_content)
    print(f"  ✅ GK.m3u: {len(gk_blocks)} channels")

    # ── 5. Write omni.m3u ────────────────────────────────────────
    total = len(ordered_jio) + len(gk_blocks)
    print(f"\n[5/5] Writing {total} channels → {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(tmpl_header + "\n")
        for block in ordered_jio:
            for line in block:
                f.write(line + "\n")
        for block in gk_blocks:
            for line in block:
                f.write(line + "\n")

    print(f"  ✅ Done!")
    print("\n✅ SUCCESS — omni.m3u generated!")
    print("=" * 62)

if __name__ == "__main__":
    main()
