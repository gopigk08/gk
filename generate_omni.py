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
RETRY_DELAY   = 5   # seconds between retries
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url, retries=RETRY_COUNT):
    """Fetch URL with retries and returns decoded text, or empty string on failure."""
    print(f"  Fetching: {url[:80]}...")
    ctx = make_ssl_ctx()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "sktechtv",
            "Accept": "*/*",
        }
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                print(f"  ✅ Fetched {len(data):,} bytes")
                return data
        except urllib.error.HTTPError as e:
            print(f"  ⚠️  HTTP {e.code} on attempt {attempt}/{retries}: {url}")
        except Exception as e:
            print(f"  ⚠️  Error on attempt {attempt}/{retries}: {e}")
        if attempt < retries:
            time.sleep(RETRY_DELAY)
    print(f"  ❌ All {retries} attempts failed for: {url}")
    return ""

def get_channel_id(block_lines):
    """Extract tvg-id or fallback to channel name from an EXTINF block."""
    for line in block_lines:
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-id="([^"]+)"', line)
            if m and m.group(1).strip():
                return m.group(1).strip()
            # Fallback: use the channel name after the last comma
            parts = line.split(",")
            if len(parts) > 1:
                return parts[-1].strip()
    return None

def parse_m3u(content):
    """Return (header_line, list_of_blocks). Each block is a list of lines."""
    lines = content.strip().splitlines()
    header = ""
    if lines and lines[0].startswith("#EXTM3U"):
        header = lines[0]
        lines = lines[1:]

    blocks = []
    current = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        current.append(line)
        if not line.startswith("#"):
            # URL line → block complete
            blocks.append(current)
            current = []

    return header, blocks

def main():
    print("=" * 60)
    print("  OMNI M3U Generator")
    print("=" * 60)

    # ── 1. Read Template ──────────────────────────────────────────────
    print(f"\n[1/4] Reading template: {TEMPLATE_FILE}")
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ Template '{TEMPLATE_FILE}' not found in repository!")
        print("   Please upload your JIO TV playlist as 'template.m3u'")
        sys.exit(1)

    with open(TEMPLATE_FILE, "r", encoding="utf-8", errors="replace") as f:
        template_content = f.read()

    tmpl_header, tmpl_blocks = parse_m3u(template_content)
    tmpl_ids = []
    for b in tmpl_blocks:
        cid = get_channel_id(b)
        if cid:
            tmpl_ids.append(cid)

    print(f"  ✅ Template has {len(tmpl_blocks)} channel blocks ({len(tmpl_ids)} with valid IDs)")

    # ── 2. Fetch Fresh Jio TV ─────────────────────────────────────────
    print(f"\n[2/4] Fetching fresh Jio TV playlist...")
    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        print("❌ Could not fetch Jio TV playlist. Aborting.")
        sys.exit(1)

    _, jio_blocks = parse_m3u(jio_content)
    jio_dict = {}
    for b in jio_blocks:
        cid = get_channel_id(b)
        if cid:
            jio_dict[cid] = b

    print(f"  ✅ Fresh Jio TV has {len(jio_blocks)} channels ({len(jio_dict)} with valid IDs)")

    # ── 3. Match Channels from Template → Fresh ───────────────────────
    print(f"\n[3/4] Matching template channels to fresh playlist...")
    ordered_jio = []
    missing = []
    for cid in tmpl_ids:
        if cid in jio_dict:
            ordered_jio.append(jio_dict[cid])
        else:
            missing.append(cid)

    print(f"  ✅ Matched: {len(ordered_jio)} channels")
    if missing:
        print(f"  ⚠️  Missing ({len(missing)}):")
        for m in missing[:10]:   # Show max 10 to keep logs readable
            print(f"     - {m}")
        if len(missing) > 10:
            print(f"     ... and {len(missing) - 10} more")

    # ── 4. Fetch GK.m3u ──────────────────────────────────────────────
    print(f"\n[4/4] Fetching GK.m3u...")
    gk_content = fetch_url(GK_URL)
    _, gk_blocks = parse_m3u(gk_content)
    print(f"  ✅ GK.m3u has {len(gk_blocks)} channels")

    # ── 5. Write omni.m3u ─────────────────────────────────────────────
    print(f"\n[5/5] Writing output: {OUTPUT_FILE}")
    total = len(ordered_jio) + len(gk_blocks)
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(tmpl_header + "\n")
        for block in ordered_jio:
            for line in block:
                f.write(line + "\n")
        for block in gk_blocks:
            for line in block:
                f.write(line + "\n")

    print(f"  ✅ Written {total} total channels to {OUTPUT_FILE}")
    print("\n✅ SUCCESS — omni.m3u is ready!")
    print("=" * 60)

if __name__ == "__main__":
    main()
