#!/usr/bin/env python3
"""Extract artboards, texts, colors, fonts and images from an Adobe XD (.xd) file.

An .xd file is a zip archive:
  manifest                                  artboard list (names, bounds)
  artwork/<artboard-path>/graphics/graphicContent.agc   JSON scene graph
  resources/<uid>                           embedded images (no extension)

Usage:
  python xd_extract.py <file.xd> <out_dir> [--frames-dir <folder of PNGs exported from XD>]

Writes <out_dir>/design.json, <out_dir>/images/*, and <out_dir>/frames/*.png (if --frames-dir given).
Only the standard library is used.
"""
import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from collections import Counter

MAGIC = [
    (b"\x89PNG", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF8", ".gif"),
    (b"RIFF", ".webp"),
    (b"<svg", ".svg"),
    (b"<?xml", ".svg"),
    (b"%PDF", ".pdf"),
]


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s or "").strip("-").lower()
    return s or "untitled"


def sniff_ext(data):
    for magic, ext in MAGIC:
        if data.startswith(magic):
            return ext
    return ".bin"


def hex_color(c):
    """XD colors look like {"mode":"RGB","value":{"r":255,"g":0,"b":0}, "alpha":1}."""
    if not isinstance(c, dict):
        return None
    v = c.get("value", c)
    try:
        r, g, b = int(v["r"]), int(v["g"]), int(v["b"])
    except (KeyError, TypeError, ValueError):
        return None
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def load_json(zf, name):
    with zf.open(name) as f:
        return json.loads(f.read().decode("utf-8"))


def find_artboards(manifest):
    """Return [{id, name, path, bounds}] for every artboard in the manifest."""
    out = []

    def walk(node, under_artwork=False):
        if not isinstance(node, dict):
            return
        path = node.get("path", "")
        if under_artwork and path.startswith("artboard-"):
            out.append({
                "id": node.get("id", path),
                "name": node.get("name", path),
                "path": path,
                "bounds": node.get("uxdesign#bounds") or {},
            })
        for child in node.get("children", []) or []:
            walk(child, under_artwork or path == "artwork")

    walk(manifest)
    return out


def walk_scene(node, ox, oy, frame, colors, fonts, uid_to_file):
    """Recursively collect texts, image fills and colors. ox/oy = accumulated offset."""
    if isinstance(node, list):
        for n in node:
            walk_scene(n, ox, oy, frame, colors, fonts, uid_to_file)
        return
    if not isinstance(node, dict):
        return

    t = node.get("transform") or {}
    x = ox + float(t.get("tx", 0) or 0)
    y = oy + float(t.get("ty", 0) or 0)
    style = node.get("style") or {}
    fill = style.get("fill") or {}
    ntype = node.get("type")

    if fill.get("type") == "solid":
        hx = hex_color(fill.get("color"))
        if hx:
            colors[hx] += 1

    if fill.get("type") == "pattern":
        pattern = fill.get("pattern") or {}
        uid = ((pattern.get("meta") or {}).get("ux") or {}).get("uid")
        if not uid and pattern.get("href"):
            uid = os.path.splitext(os.path.basename(pattern["href"]))[0]
        shape = node.get("shape") or {}
        if uid:
            frame["images"].append({
                "name": node.get("name", ""),
                "file": uid_to_file.get(uid),
                "uid": uid,
                "x": round(x), "y": round(y),
                "w": round(float(shape.get("width", pattern.get("width", 0)) or 0)),
                "h": round(float(shape.get("height", pattern.get("height", 0)) or 0)),
            })

    if ntype == "text":
        text = node.get("text") or {}
        raw = text.get("rawText", "")
        font = style.get("font") or {}
        color = hex_color(fill.get("color")) if fill.get("type") == "solid" else None
        family = font.get("family") or font.get("postscriptName")
        if family:
            fonts[(family, font.get("style", ""), font.get("size"))] += 1
        if raw.strip():
            frame["texts"].append({
                "text": raw,
                "font": family,
                "style": font.get("style"),
                "size": font.get("size"),
                "color": color,
                "x": round(x), "y": round(y),
                "name": node.get("name", ""),
            })

    for key in ("children",):
        if key in node:
            walk_scene(node[key], x, y, frame, colors, fonts, uid_to_file)
    for container in ("artboard", "group", "syncSourceGuid", "meta"):
        sub = node.get(container)
        if isinstance(sub, dict) and "children" in sub:
            walk_scene(sub["children"], x, y, frame, colors, fonts, uid_to_file)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xd_file")
    ap.add_argument("out_dir")
    ap.add_argument("--frames-dir", help="folder of artboard PNGs exported from XD (File > Export > PNG)")
    args = ap.parse_args()

    img_dir = os.path.join(args.out_dir, "images")
    frames_dir = os.path.join(args.out_dir, "frames")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(frames_dir, exist_ok=True)

    with zipfile.ZipFile(args.xd_file) as zf:
        names = zf.namelist()

        # 1. images
        uid_to_file = {}
        images = []
        for n in names:
            if not n.startswith("resources/") or n.endswith("/"):
                continue
            data = zf.read(n)
            if len(data) < 64:
                continue
            uid = os.path.basename(n)
            ext = sniff_ext(data[:16])
            if ext in (".bin", ".pdf"):
                continue
            fname = uid + ext
            with open(os.path.join(img_dir, fname), "wb") as f:
                f.write(data)
            uid_to_file[uid] = "images/" + fname
            images.append({"file": "images/" + fname, "uid": uid, "bytes": len(data)})

        # 2. artboards
        manifest = load_json(zf, "manifest") if "manifest" in names else {}
        artboards = find_artboards(manifest)
        colors, fonts = Counter(), Counter()
        frames = []
        for ab in artboards:
            agc = "artwork/{}/graphics/graphicContent.agc".format(ab["path"])
            frame = {
                "id": ab["id"], "name": ab["name"], "slug": slugify(ab["name"]),
                "width": ab["bounds"].get("width"), "height": ab["bounds"].get("height"),
                "png": None, "texts": [], "images": [],
            }
            if agc in names:
                scene = load_json(zf, agc)
                bx = -float(ab["bounds"].get("x", 0) or 0)
                by = -float(ab["bounds"].get("y", 0) or 0)
                walk_scene(scene.get("children", []), bx, by, frame, colors, fonts, uid_to_file)
            frame["texts"].sort(key=lambda t: (t["y"], t["x"]))
            frame["images"].sort(key=lambda i: (i["y"], i["x"]))
            frames.append(frame)

        # 3. preview thumbnail, if XD stored one
        for n in names:
            if n.lower() in ("preview.png", "thumbnail.png", "renditions/thumbnail.png"):
                with open(os.path.join(args.out_dir, "preview.png"), "wb") as f:
                    f.write(zf.read(n))
                break

    # 4. match exported artboard PNGs by name
    if args.frames_dir and os.path.isdir(args.frames_dir):
        exported = {slugify(os.path.splitext(f)[0]): f for f in os.listdir(args.frames_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))}
        for fr in frames:
            src = exported.get(fr["slug"])
            if src:
                dst = os.path.join(frames_dir, fr["slug"] + os.path.splitext(src)[1].lower())
                shutil.copyfile(os.path.join(args.frames_dir, src), dst)
                fr["png"] = os.path.relpath(dst, args.out_dir).replace("\\", "/")

    design = {
        "source": "xd",
        "source_file": os.path.abspath(args.xd_file),
        "frames": frames,
        "colors": [{"hex": h, "count": c} for h, c in colors.most_common()],
        "fonts": [{"family": f, "style": s, "size": z, "count": c}
                  for (f, s, z), c in fonts.most_common()],
        "images": images,
    }
    with open(os.path.join(args.out_dir, "design.json"), "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2, ensure_ascii=False)

    missing_png = [fr["name"] for fr in frames if not fr["png"]]
    print(json.dumps({
        "frames": len(frames), "images": len(images), "colors": len(colors),
        "fonts": len(fonts), "frames_without_png": missing_png,
    }, indent=2))


if __name__ == "__main__":
    sys.exit(main())
