# Test lanes

From the standalone pack root:

```sh
node --test phenoDesign-overlay/packages/visual-production/test/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
python tests/browser_canary.py
node scripts/check_syntax.cjs
```

The JS regression suite uses only Node built-ins (Node 20+). The Python suite uses the standard library plus installed FFmpeg/FFprobe for real media tests; its clip is clearly synthetic and included. Browser tests additionally need Python Playwright and a separately installed Chromium executable (`PD_CHROMIUM` selects its path). The syntax helper requires an installed TypeScript module; it does not resolve React/Remotion dependencies or typecheck native APIs.

The preparation browser policy blocked navigation. Browser tests therefore load the exact local HTML fixture with `set_content`; they exercise actual Chromium DOM/SVG/CSS/input behavior, but do not qualify HTTP delivery, routing, headers, hosting or a real product page. No navigation policy was weakened. The browser launch is isolated; `--no-sandbox` is used only for this restricted preparation container and should be removed on hosts with a working browser sandbox. Do not use a personal browser profile.

Full native host and actual Remotion E2E lanes are described in the docs/backlog and are NOT counted as passing by these scripts. The original kit's tests/evidence remain historical references and are not included in the v2 passing totals.
