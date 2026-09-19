#!/usr/bin/env python3
"""Extract frontend/index.html CSS to styles.css; JS stays in app.js."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "frontend" / "index.html"
OUT = ROOT / "frontend"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    if 'href="styles.css"' in text and (OUT / "app.js").exists():
        print("Already split; skipping")
        return

    style_start = text.index("<style>") + len("<style>")
    style_end = text.index("</style>")
    css = text[style_start:style_end].strip() + "\n"

    body_start = text.index("</head>") + len("</head>")
    gsap_tag = text.index('<script src="https://cdn.jsdelivr.net/npm/gsap')
    html = text[body_start:gsap_tag].strip() + "\n"

    js_open = text.index("<script>\n(function () {") + len("<script>\n")
    js_close = text.rindex("})();\n  </script>")
    app_js = "(function () {\n  \"use strict\";\n\n" + text[js_open:js_close].strip() + "\n})();\n"

    motion_marker = "  var CredaStageMachine = {"
    motion_start = app_js.index(motion_marker)
    motion_end = app_js.index("  var session = { caseId: null, token: null };")
    motion_js = (
        "(function () {\n  \"use strict\";\n"
        + app_js[motion_start:motion_end].strip()
        + "\n\n  window.CredaStageMachine = CredaStageMachine;\n"
        + "  window.WaitStoryboard = WaitStoryboard;\n"
        + "  window.CredaShieldArt = CredaShieldArt;\n"
        + "  window.CredaMotion = CredaMotion;\n"
        + "})();\n"
    )
    app_body = (
        app_js[:motion_start]
        + "  var CredaStageMachine = window.CredaStageMachine;\n"
        + "  var WaitStoryboard = window.WaitStoryboard;\n"
        + "  var CredaShieldArt = window.CredaShieldArt;\n"
        + "  var CredaMotion = window.CredaMotion;\n"
        + app_js[motion_end:]
    )

    head = text[: text.index("<style>")]
    build = re.search(r'name="creda-build" content="([^"]+)"', head).group(1)
    head = head.replace(
        "  <style>",
        '  <link rel="stylesheet" href="styles.css" />',
    )
    head = head.replace(
        f'content="{build}"',
        f'content="{build}-split"',
    )

    index = head + "\n" + html
    index += '\n  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.7/dist/gsap.min.js"></script>\n'
    index += '  <script src="motion.js"></script>\n'
    index += '  <script src="app.js"></script>\n'
    index += "</body>\n</html>\n"

    (OUT / "styles.css").write_text(css, encoding="utf-8")
    (OUT / "motion.js").write_text(motion_js, encoding="utf-8")
    (OUT / "app.js").write_text(app_body, encoding="utf-8")
    SRC.write_text(index, encoding="utf-8")
    print("Wrote styles.css, motion.js, app.js")


if __name__ == "__main__":
    main()
