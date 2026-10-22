#!/usr/bin/env python3
"""Extract frames, texts, colors, fonts and images from a Figma file via the REST API.

Usage:
  python figma_extract.py <figma-url> <out_dir> [--token TOKEN] [--scale 1]

The token comes from --token or the FIGMA_TOKEN environment variable
(Figma > Settings > Security > Personal access tokens, scope: file content read).

If the URL has ?node-id=..., only that node is extracted (a frame, section or page);
otherwise every top-level frame of every page.

Writes <out_dir>/design.json, <out_dir>/frames/*.png (rendered frames),
<out_dir>/images/* (image fills) and <out_dir>/exports/* (nodes with export settings).
Only the standard library is used.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

API = "https://api.figma.com/v1"
FRAME_TYPES = {"FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"}


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s or "").strip("-").lower()
    return s or "untitled"


def parse_url(url):
    m = re.search(r"figma\.com/(?:file|design|proto)/([A-Za-z0-9]+)", url)
    if not m:
        sys.exit("Not a Figma file URL: " + url)
    key = m.group(1)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    node = q.get("node-id", [None])[0]
    if node:
        node = node.replace("-", ":")
    return key, node


def get(url, token, binary=False, retries=4):
    req = urllib.request.Request(url, headers={"X-Figma-Token": token} if token else {})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
                return data if binary else json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(int(e.headers.get("Retry-After", "10")))
                continue
            if e.code == 403:
                sys.exit("Figma API 403: token missing/invalid or no access to this file.")
            raise


def hex_color(c, opacity=1.0):
    if not c:
        return None
    r, g, b = (round(c.get(k, 0) * 255) for k in ("r", "g", "b"))
    a = c.get("a", 1) * opacity
    return "#{:02x}{:02x}{:02x}".format(r, g, b) + ("" if a >= 0.999 else "{:02x}".format(round(a * 255)))


def collect_frames(node):
    """Frames to extract from the given root (document, canvas, section or frame)."""
    t = node.get("type")
    if t in FRAME_TYPES:
        return [node]
    if t == "DOCUMENT":
        out = []
        for page in node.get("children", []):
            out += collect_frames(page)
        return out
    # CANVAS / SECTION / GROUP: their direct frame children
    out = []
    for ch in node.get("children", []):
        if ch.get("type") in FRAME_TYPES:
            out.append(ch)
        elif ch.get("type") == "SECTION":
            out += collect_frames(ch)
    return out


def walk(node, frame, origin, colors, fonts, image_refs, exports):
    if node.get("visible") is False:
        return
    box = node.get("absoluteBoundingBox") or {}
    x = round(box.get("x", 0) - origin[0])
    y = round(box.get("y", 0) - origin[1])
    w, h = round(box.get("width", 0)), round(box.get("height", 0))

    for fill in node.get("fills", []) or []:
        if fill.get("visible") is False:
            continue
        if fill.get("type") == "SOLID":
            hx = hex_color(fill.get("color"), fill.get("opacity", 1))
            if hx:
                colors[hx] += 1
        elif fill.get("type") == "IMAGE" and fill.get("imageRef"):
            image_refs.add(fill["imageRef"])
            frame["images"].append({
                "name": node.get("name", ""), "ref": fill["imageRef"],
                "file": None, "scale_mode": fill.get("scaleMode"),
                "x": x, "y": y, "w": w, "h": h,
            })

    if node.get("type") == "TEXT":
        st = node.get("style") or {}
        fill = next((f for f in node.get("fills", []) if f.get("type") == "SOLID"), None)
        family = st.get("fontFamily")
        if family:
            fonts[(family, st.get("fontWeight"), st.get("fontSize"))] += 1
        frame["texts"].append({
            "text": node.get("characters", ""),
            "font": family, "weight": st.get("fontWeight"), "size": st.get("fontSize"),
            "line_height": st.get("lineHeightPx"), "letter_spacing": st.get("letterSpacing"),
            "align": st.get("textAlignHorizontal"), "case": st.get("textCase"),
            "color": hex_color(fill.get("color"), fill.get("opacity", 1)) if fill else None,
            "x": x, "y": y, "w": w, "h": h, "name": node.get("name", ""),
        })

    if node.get("exportSettings") and node is not frame.get("_node"):
        es = node["exportSettings"][0]
        exports.append({"id": node["id"], "name": node.get("name", ""),
                        "format": es.get("format", "PNG").lower(),
                        "x": x, "y": y, "w": w, "h": h, "frame": frame["slug"]})

    for ch in node.get("children", []) or []:
        walk(ch, frame, origin, colors, fonts, image_refs, exports)


def download(url, path):
    with urllib.request.urlopen(url, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())


def ext_for(data_start):
    if data_start.startswith(b"\x89PNG"):
        return ".png"
    if data_start.startswith(b"\xff\xd8"):
        return ".jpg"
    if data_start.startswith(b"GIF8"):
        return ".gif"
    return ".png"


def render(key, ids, fmt, scale, token):
    """Render node ids -> {id: url}, in chunks to stay under URL limits."""
    out = {}
    ids = list(ids)
    for i in range(0, len(ids), 40):
        chunk = ",".join(ids[i:i + 40])
        q = urllib.parse.urlencode({"ids": chunk, "format": fmt, "scale": scale})
        res = get(f"{API}/images/{key}?{q}", token)
        out.update({k: v for k, v in (res.get("images") or {}).items() if v})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out_dir")
    ap.add_argument("--token", default=os.environ.get("FIGMA_TOKEN"))
    ap.add_argument("--scale", default="1")
    args = ap.parse_args()
    if not args.token:
        sys.exit("No Figma token. Pass --token or set FIGMA_TOKEN.")

    key, node_id = parse_url(args.url)
    for d in ("frames", "images", "exports"):
        os.makedirs(os.path.join(args.out_dir, d), exist_ok=True)

    if node_id:
        res = get(f"{API}/files/{key}/nodes?ids={urllib.parse.quote(node_id)}", token=args.token)
        root = res["nodes"][node_id]["document"]
        file_name = res.get("name")
    else:
        res = get(f"{API}/files/{key}", token=args.token)
        root = res["document"]
        file_name = res.get("name")

    colors, fonts, image_refs, exports = Counter(), Counter(), set(), []
    frames = []
    used_slugs = Counter()
    for fn in collect_frames(root):
        box = fn.get("absoluteBoundingBox") or {}
        slug = slugify(fn.get("name"))
        used_slugs[slug] += 1
        if used_slugs[slug] > 1:
            slug = f"{slug}-{used_slugs[slug]}"
        frame = {"id": fn["id"], "name": fn.get("name"), "slug": slug,
                 "width": box.get("width"), "height": box.get("height"),
                 "png": None, "texts": [], "images": [], "_node": fn}
        walk(fn, frame, (box.get("x", 0), box.get("y", 0)), colors, fonts, image_refs, exports)
        frame["texts"].sort(key=lambda t: (t["y"], t["x"]))
        frame["images"].sort(key=lambda i: (i["y"], i["x"]))
        frames.append(frame)

    # 1. rendered frames (reference screenshots for planning and QA)
    renders = render(key, [f["id"] for f in frames], "png", args.scale, args.token)
    for f in frames:
        if f["id"] in renders:
            rel = f"frames/{f['slug']}.png"
            download(renders[f["id"]], os.path.join(args.out_dir, rel))
            f["png"] = rel

    # 2. image fills (photos, backgrounds)
    ref_urls = (get(f"{API}/files/{key}/images", args.token).get("meta") or {}).get("images") or {}
    ref_to_file, images = {}, []
    for ref in sorted(image_refs):
        url = ref_urls.get(ref)
        if not url:
            continue
        with urllib.request.urlopen(url, timeout=180) as r:
            data = r.read()
        rel = "images/" + ref + ext_for(data[:8])
        with open(os.path.join(args.out_dir, rel), "wb") as fh:
            fh.write(data)
        ref_to_file[ref] = rel
        images.append({"file": rel, "ref": ref, "bytes": len(data)})
    for f in frames:
        for im in f["images"]:
            im["file"] = ref_to_file.get(im["ref"])

    # 3. nodes the designer marked for export (icons, logos)
    by_fmt = {}
    for e in exports:
        by_fmt.setdefault(e["format"], []).append(e)
    for fmt, items in by_fmt.items():
        urls = render(key, [e["id"] for e in items], fmt if fmt in ("png", "jpg", "svg", "pdf") else "png",
                      args.scale, args.token)
        for e in items:
            if e["id"] in urls:
                rel = f"exports/{e['frame']}--{slugify(e['name'])}.{fmt}"
                download(urls[e["id"]], os.path.join(args.out_dir, rel))
                e["file"] = rel

    for f in frames:
        f.pop("_node", None)
    design = {
        "source": "figma", "file_key": key, "file_name": file_name, "node_id": node_id,
        "frames": frames,
        "colors": [{"hex": h, "count": c} for h, c in colors.most_common()],
        "fonts": [{"family": fa, "weight": w, "size": s, "count": c}
                  for (fa, w, s), c in fonts.most_common()],
        "images": images,
        "exports": exports,
    }
    with open(os.path.join(args.out_dir, "design.json"), "w", encoding="utf-8") as fh:
        json.dump(design, fh, indent=2, ensure_ascii=False)

    print(json.dumps({"frames": len(frames), "images": len(images), "exports": len(exports),
                      "colors": len(colors), "fonts": len(fonts)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
