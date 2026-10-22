#!/usr/bin/env python3
"""Upload extracted design images to the WordPress media library.

Usage:
  python wp_upload_media.py <design_dir> [--connection ~/.rp-command/connection.json]

Uploads every file under <design_dir>/images and <design_dir>/exports through the
core REST endpoint /wp-json/wp/v2/media (Application Password auth), and writes
<design_dir>/media-map.json:  { "images/abc.png": {"id": 123, "url": "...", "sha1": "..."} }

Re-running skips files already in media-map.json with the same sha1.
SVGs are not uploaded (WordPress blocks them by default); they are listed under
"svg_pending" for the builder agent to handle (e.g. rp/elementor-upload-svg).

connection.json:
  {"site_url": "https://example.com", "username": "admin", "app_password": "xxxx xxxx ...",
   "staging_user": "", "staging_password": ""}   # staging_* only for sites behind Basic-Auth
"""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

UPLOAD_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def basic(user, pw):
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design_dir")
    ap.add_argument("--connection", default=os.path.join(os.path.expanduser("~"), ".rp-command", "connection.json"))
    args = ap.parse_args()

    with open(args.connection, encoding="utf-8") as f:
        conn = json.load(f)
    endpoint = conn["site_url"].rstrip("/") + "/wp-json/wp/v2/media"
    headers = {}
    if conn.get("staging_user"):
        # Site Basic-Auth uses Authorization; RP Connect reads the app password from X-RP-Authorization.
        headers["Authorization"] = basic(conn["staging_user"], conn.get("staging_password", ""))
        headers["X-RP-Authorization"] = basic(conn["username"], conn["app_password"])
    else:
        headers["Authorization"] = basic(conn["username"], conn["app_password"])

    map_path = os.path.join(args.design_dir, "media-map.json")
    media_map = {}
    if os.path.exists(map_path):
        with open(map_path, encoding="utf-8") as f:
            media_map = json.load(f)
        media_map.pop("svg_pending", None)
    svg_pending = []
    failed = []
    uploaded = 0

    for sub in ("images", "exports"):
        folder = os.path.join(args.design_dir, sub)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            rel = f"{sub}/{name}"
            path = os.path.join(folder, name)
            ext = os.path.splitext(name)[1].lower()
            if ext == ".svg":
                svg_pending.append(rel)
                continue
            if ext not in UPLOAD_EXT:
                continue
            with open(path, "rb") as f:
                data = f.read()
            sha1 = hashlib.sha1(data).hexdigest()
            if media_map.get(rel, {}).get("sha1") == sha1:
                continue
            req = urllib.request.Request(endpoint, data=data, method="POST", headers={
                **headers,
                "Content-Type": mimetypes.guess_type(name)[0] or "application/octet-stream",
                "Content-Disposition": f'attachment; filename="{name}"',
            })
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    res = json.loads(r.read().decode("utf-8"))
                media_map[rel] = {"id": res["id"], "url": res.get("source_url"), "sha1": sha1,
                                  "width": (res.get("media_details") or {}).get("width"),
                                  "height": (res.get("media_details") or {}).get("height")}
                uploaded += 1
            except urllib.error.HTTPError as e:
                failed.append({"file": rel, "status": e.code, "body": e.read().decode("utf-8", "replace")[:300]})
                if e.code in (401, 403):
                    break
            with open(map_path, "w", encoding="utf-8") as f:
                json.dump(media_map, f, indent=2)

    media_map_out = dict(media_map)
    if svg_pending:
        media_map_out["svg_pending"] = svg_pending
    with open(map_path, "w", encoding="utf-8") as f:
        json.dump(media_map_out, f, indent=2)

    print(json.dumps({"uploaded": uploaded, "total_in_map": len(media_map),
                      "svg_pending": len(svg_pending), "failed": failed}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
