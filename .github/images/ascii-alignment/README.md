# Bilingual ASCII alignment evidence

Chromium via Playwright 1.62.1, Hugo Extended 0.168.0.
Before: b8a88f8c27844c32042c50ee2b43404b5ce95fb3.
After: 5d7e6f92c91d9d4907d8e727cd7e89c406fd19f8.
Workflow: https://github.com/hugegraph/hugegraph-doc/actions/runs/40634218501

Desktop: 1440 x 1000, diagram crops. Mobile: 390 x 844.
English and Chinese Docs landing and introduction pages were checked.
DOM Range measured every line's last glyph at the same x coordinate:
maximum right-edge difference 0 CSS pixels on all four desktop diagrams.
Mobile document width stayed within the viewport; code retains native horizontal scrolling.
Both builds use their own matching local resources via production-origin request remapping.
Source/link checks and 290 Python tests passed (one conditional rendered-output skip).
No theme or stylesheet changes; plain ASCII avoids Unicode box-drawing font fallback.
