# Preparation failures and corrections

- Chromium rejected both file URL and loopback HTTP navigation with ERR_BLOCKED_BY_ADMINISTRATOR. The test lane was narrowed to direct loading of the package's HTML fixture through Playwright set_content. Navigation remains untested; no policy settings were changed.
- The first reviewed desktop screenshot captured an in-progress reset interpolation: the displayed value had reset before the needle's visual transition settled. The test now waits for the computed transform to reach the corresponding state and checks it before taking the retained screenshot. This is why source/state assertions alone were not considered enough.
- Playwright's string-evaluating wait_for_function conflicted with the page's restrictive content security policy. The page policy was retained; the test uses bounded external polling of the existing element's computed transform instead.
- Container git cloning failed because external DNS/network was unavailable. Repository claims are based on connector source reads, not an invented local build.
- Native Adobe, Blender, Rive and Remotion execution were unavailable. This limitation is carried through the docs, backlog and final validation report rather than being replaced with synthetic success.
