//! Compiled, minified CSS for the inbox web frontend.

/// Compiled, minified CSS for the inbox web frontend.
#[must_use]
pub fn full_html_css() -> &'static str {
    concat!(
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}",
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f5f5f7;color:#1d1d1f;line-height:1.5;padding:1rem;max-width:720px;margin:0 auto}",
        "a{color:#0066cc;text-decoration:none;font-weight:500}",
        "a:hover{text-decoration:underline}",
        "header{display:flex;align-items:baseline;gap:.75rem;margin-bottom:1.5rem;padding-bottom:.75rem;border-bottom:1px solid #d2d2d7}",
        "header h1{font-size:1.5rem;font-weight:600}",
        ".badge{display:inline-block;background:#0066cc;color:#fff;font-size:.75rem;font-weight:600;padding:.125rem .5rem;border-radius:99px;line-height:1.4}",
        ".card{display:block;background:#fff;border-radius:10px;padding:.75rem 1rem;margin-bottom:.5rem;border:1px solid #e5e5ea;transition:box-shadow .15s}",
        ".card:hover{box-shadow:0 2px 8px rgba(0,0,0,.08)}",
        ".row{display:flex;flex-direction:column;gap:.25rem}",
        ".row-main{display:flex;justify-content:space-between;align-items:baseline;gap:.5rem}",
        ".row-main strong{font-size:1rem;font-weight:600}",
        ".row-main .ago{font-size:.8125rem;color:#86868b;white-space:nowrap}",
        ".row-sub{display:flex;justify-content:space-between;font-size:.8125rem;color:#6e6e73;gap:.5rem}",
        ".warn{border-left:4px solid #ff9f0a;padding-left:calc(1rem - 4px)}",
        ".urgent{border-left:4px solid #ff453a;padding-left:calc(1rem - 4px)}",
        "footer{margin-top:2rem;font-size:.8125rem;color:#86868b;text-align:center}",
        ".empty{text-align:center;padding:3rem 1rem;color:#86868b}",
        ".empty p{font-size:1.125rem;margin-bottom:.5rem}",
        ".expired{opacity:.55}",
        ".expired .badge{background:#86868b}",
        ".expired-notice{color:#86868b;font-style:italic}",
        "main.card{background:#fff;border-radius:10px;padding:1.5rem;border:1px solid #e5e5ea}",
        "main.card h2{font-size:1.25rem;font-weight:600;margin-bottom:.5rem}",
        "main.card p{color:#515154;margin-bottom:1rem;line-height:1.6}",
        "main.card .ok{display:inline-block;margin-top:.5rem;font-weight:500}",
        "pre{background:#f0f0f2;padding:.75rem;border-radius:8px;overflow-x:auto;font-size:.8125rem;margin:.5rem 0}",
        "@media(prefers-color-scheme:dark){body{background:#1c1c1e;color:#f5f5f7}a{color:#409cff}.card,.card.main{background:#2c2c2e;border-color:#38383a}.badge{background:#409cff}.row-sub,.ago,.empty,.footer{color:#98989d}header{border-color:#38383a}pre{background:#2c2c2e}}",
        "@media(max-width:480px){body{padding:.5rem}header h1{font-size:1.25rem}.card{padding:.5rem .75rem}}",
    )
}
