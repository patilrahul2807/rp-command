#!/usr/bin/env python3
"""Per-page build checkpoints for /rp-build (resume support).

State lives in .rp/pages/<page-slug>/progress.json (project folder = current directory).

Usage:
  python checkpoint.py read <page-slug>
      Prints every phase with its status and a final line:
        NEXT_RECOMMENDED=<phase>      (first phase not done/skipped; "complete" when all done)
  python checkpoint.py mark <page-slug> <phase> [done|failed|skipped|pending] [--note "text"]
  python checkpoint.py page-can-start <page-slug>
      Exit 0 and "CAN_START=yes" if every page listed before it in project-config.json `pages`
      has approvals.pages.<slug>.status == "approved"; otherwise exit 1 and "CAN_START=no BLOCKED_BY=<slug>".
  python checkpoint.py reset <page-slug> [<phase>]
      Reset one phase (and every later phase) or the whole page to pending.

The phase list is chosen from .rp/project-config.json: `builder` + whether `design.source` is "html".
Only the standard library is used.
"""
import argparse
import datetime
import json
import os
import re
import sys

RP = ".rp"
CONFIG = os.path.join(RP, "project-config.json")

PHASES = {
    "acf": ["design-extracted", "extraction-validated", "sections-analyzed", "planned",
            "plan-approved", "theme-setup", "fields-created", "templates-built",
            "theme-pushed", "page-assembled", "qa-passed", "checkpointed"],
    "acf-html": ["html-extracted", "reference-captured", "spec-parsed", "spec-approved",
                 "acf-planned", "plan-approved", "theme-built", "deployed", "qa-passed",
                 "audited", "checkpointed"],
    "elementor": ["design-extracted", "extraction-validated", "planned", "plan-approved",
                  "foundation-built", "sections-built", "globals-verified", "page-verified",
                  "qa-passed", "checkpointed"],
    "elementor-html": ["html-native-built", "page-verified", "qa-passed", "checkpointed"],
    "gutenberg": ["design-extracted", "extraction-validated", "planned", "plan-approved",
                  "theme-json-built", "theme-built", "page-built", "globals-enforced",
                  "page-verified", "qa-passed", "checkpointed"],
    "avada": ["design-extracted", "extraction-validated", "planned", "plan-approved",
              "globals-built", "page-built", "cache-cleared", "page-verified", "qa-passed",
              "checkpointed"],
}
DONE = {"done", "skipped"}
STATUSES = {"done", "failed", "skipped", "pending"}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def load_config():
    if not os.path.exists(CONFIG):
        sys.exit(f"ERROR: {CONFIG} not found — run /rp-command:rp-start first.")
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def profile(cfg):
    builder = (cfg.get("builder") or "").lower()
    if builder not in ("acf", "elementor", "gutenberg", "avada"):
        sys.exit(f"ERROR: unknown builder '{builder}' in {CONFIG}.")
    source = ((cfg.get("design") or {}).get("source") or "").lower()
    key = f"{builder}-html" if source == "html" and f"{builder}-html" in PHASES else builder
    return key, PHASES[key]


def state_path(slug):
    return os.path.join(RP, "pages", slug, "progress.json")


def load_state(slug, key):
    path = state_path(slug)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            st = json.load(f)
        if st.get("profile") == key:
            return st
    return {"page": slug, "profile": key, "phases": {}}


def save_state(slug, st):
    path = state_path(slug)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def cmd_read(slug):
    key, phases = profile(load_config())
    st = load_state(slug, key)
    print(f"PAGE={slug} PROFILE={key}")
    nxt = None
    for ph in phases:
        rec = st["phases"].get(ph, {})
        status = rec.get("status", "pending")
        note = f"  # {rec['note']}" if rec.get("note") else ""
        print(f"{ph:24} {status}{note}")
        if nxt is None and status not in DONE:
            nxt = ph
    print(f"NEXT_RECOMMENDED={nxt or 'complete'}")


def cmd_mark(slug, phase, status, note):
    key, phases = profile(load_config())
    if phase not in phases:
        sys.exit(f"ERROR: '{phase}' is not a phase of profile '{key}': {', '.join(phases)}")
    if status not in STATUSES:
        sys.exit(f"ERROR: status must be one of {sorted(STATUSES)}")
    st = load_state(slug, key)
    st["phases"][phase] = {"status": status, "at": now(), **({"note": note} if note else {})}
    save_state(slug, st)
    print(f"MARKED {slug}:{phase}={status}")


def cmd_reset(slug, phase):
    key, phases = profile(load_config())
    st = load_state(slug, key)
    if phase:
        if phase not in phases:
            sys.exit(f"ERROR: '{phase}' is not a phase of profile '{key}'.")
        for ph in phases[phases.index(phase):]:
            st["phases"].pop(ph, None)
    else:
        st["phases"] = {}
    save_state(slug, st)
    print(f"RESET {slug}" + (f" from {phase}" if phase else ""))


def cmd_can_start(slug):
    cfg = load_config()
    pages = [slugify(p) for p in cfg.get("pages", [])]
    approvals = ((cfg.get("approvals") or {}).get("pages") or {})
    if slug not in pages:
        print(f"CAN_START=yes  # '{slug}' not in pages list; no ordering constraint")
        return 0
    for earlier in pages[:pages.index(slug)]:
        if (approvals.get(earlier) or {}).get("status") != "approved":
            print(f"CAN_START=no BLOCKED_BY={earlier}")
            return 1
    print("CAN_START=yes")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read"); r.add_argument("slug")
    m = sub.add_parser("mark"); m.add_argument("slug"); m.add_argument("phase")
    m.add_argument("status", nargs="?", default="done"); m.add_argument("--note")
    c = sub.add_parser("page-can-start"); c.add_argument("slug")
    x = sub.add_parser("reset"); x.add_argument("slug"); x.add_argument("phase", nargs="?")
    a = ap.parse_args()
    slug = slugify(a.slug)
    if a.cmd == "read":
        return cmd_read(slug)
    if a.cmd == "mark":
        return cmd_mark(slug, a.phase, a.status, a.note)
    if a.cmd == "reset":
        return cmd_reset(slug, a.phase)
    return cmd_can_start(slug)


if __name__ == "__main__":
    sys.exit(main())
