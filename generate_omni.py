import urllib.request
import re
import ssl

def get_channel_id(block_lines):
    for line in block_lines:
        if line.startswith('#EXTINF'):
            match = re.search(r'tvg-id="([^"]+)"', line)
            if match:
                return match.group(1)
            # Fallback to the channel name
            parts = line.split(',')
            if len(parts) > 1:
                return parts[-1].strip()
    return None

def parse_m3u_blocks(m3u_content):
    lines = m3u_content.strip().splitlines()
    header = ""
    if lines and lines[0].startswith('#EXTM3U'):
        header = lines[0]
        lines = lines[1:]
        
    blocks = []
    current_block = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        current_block.append(line)
        if not line.startswith('#'):
            # It's a URL, meaning the block is complete
            blocks.append(current_block)
            current_block = []
            
    return header, blocks

def fetch_url(url):
    print(f"Fetching {url}...")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': 'sktechtv'})
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return resp.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""

def main():
    template_file = "template.m3u" # Make sure your JIO TV.m3u is renamed to template.m3u on GitHub
    fresh_jio_url = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
    gk_url = "https://raw.githubusercontent.com/gopigk08/Omni/main/GK.m3u"
    output_file = "omni.m3u"

    print(f"Reading template {template_file}...")
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except FileNotFoundError:
        print(f"Template file '{template_file}' not found. Please upload your JIO TV.m3u as template.m3u to the repository.")
        return

    # 1. Parse Template
    template_header, template_blocks = parse_m3u_blocks(template_content)
    template_ids = []
    for b in template_blocks:
        cid = get_channel_id(b)
        if cid:
            template_ids.append(cid)
    
    print(f"Found {len(template_ids)} channels in template.")

    # 2. Fetch and Parse Fresh Jio TV
    fresh_jio_content = fetch_url(fresh_jio_url)
    if not fresh_jio_content:
        return
    _, fresh_jio_blocks = parse_m3u_blocks(fresh_jio_content)
    
    fresh_jio_dict = {}
    for b in fresh_jio_blocks:
        cid = get_channel_id(b)
        if cid:
            fresh_jio_dict[cid] = b
            
    # 3. Match and Order Jio TV
    ordered_jio_blocks = []
    for cid in template_ids:
        if cid in fresh_jio_dict:
            ordered_jio_blocks.append(fresh_jio_dict[cid])
        else:
            print(f"Warning: Channel '{cid}' from template not found in fresh Jio TV playlist.")

    # 4. Fetch GK.m3u
    gk_content = fetch_url(gk_url)
    _, gk_blocks = parse_m3u_blocks(gk_content)
    print(f"Found {len(gk_blocks)} channels in GK.m3u.")

    # 5. Output omni.m3u
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write exact header from template
        f.write(template_header + '\n')
        
        # Write ordered Jio TV blocks
        for block in ordered_jio_blocks:
            for line in block:
                f.write(line + '\n')
                
        # Write GK.m3u blocks
        for block in gk_blocks:
            for line in block:
                f.write(line + '\n')
                
    print(f"Success! {output_file} generated with {len(ordered_jio_blocks) + len(gk_blocks)} total channels.")

if __name__ == "__main__":
    main()
