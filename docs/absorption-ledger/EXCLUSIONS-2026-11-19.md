# Absorption Exclusions Ledger (2026-11-19)

Read-only classification of files present in absorbed working trees but omitted from commit because `git add` obeyed `.gitignore`.

**Method:** `python3 -u scripts/check_ignored.py apps/slipstream apps/zz-ref-HeliosCLI libs/claude-plugins-official apps/zz-ref-HeliosLite` plus per-file rule/size enumeration via `git ls-files --others --ignored --exclude-standard` and batched `git check-ignore -v --no-index` (no git state changes; no `git add -f` run).

- Total ignored/missing files analyzed: **509**
- Distinct rule groups: **14**
- Genuinely lost (CONTENT, should be preserved): **496**
- Correctly excluded (ARTIFACT): **13**

## Rule Group Classification

| Repo | Rule | Source | Count | Classification | Recommendation | Notes |
| --- | --- | --- | ---: | --- | --- | --- |
| `apps/slipstream` | `.vscode/` | `.gitignore:23` | 1 | ARTIFACT | correctly excluded | Editor/IDE launch configuration (`.vscode/launch.json`), machine-local/editor state; not required project source/content. |
| `apps/slipstream` | `.env.*` | `.gitignore:74` | 1 | CONTENT | should force-add | `clients/android/.env.template` documents required Android release/build variables with empty placeholders and explicit "DO NOT COMMIT THE .env FILE!" guidance; inspected content shows no secrets. |
| `apps/slipstream` | `vendor/` | `.gitignore:16` | 450 | CONTENT | must force-add | Vendored dependency/source/build trees required by the absorbed project (Android NDK crate sources, `pyrowave-sys/vendor/pyrowave` including Granite and bundled third-party code/headers/build files/docs/assets). Vendor trees include embedded third-party license/notice files (e.g. Granite LICENSE, Vulkan headers/volk license files); preserving them is necessary for source completeness, reproducible builds, and license retention. |
| `apps/zz-ref-HeliosCLI` | `.codex/` | `.gitignore:80` | 24 | CONTENT | should force-add | Repo-shipped Codex environment configuration and skill definitions, agents metadata, references, scripts, and tests under `.codex/`; project tooling/content rather than transient editor cache. |
| `apps/zz-ref-HeliosCLI` | `coverage/` | `.gitignore:38` | 9 | ARTIFACT | correctly excluded | Generated test/coverage/lint output and summary logs under `artifacts/coverage/` (build/test artifacts), not source records. |
| `apps/zz-ref-HeliosCLI` | `tmp-*` | `.gitignore:91` | 1 | ARTIFACT | correctly excluded | Temporary discovery output (`artifacts/phase-2/tmp-discovery-opencode.json`). |
| `apps/zz-ref-HeliosCLI` | `audit_scorecard.json` | `.gitignore:117` | 1 | CONTENT | should force-add | `audit_scorecard.json` is a checked-in audit scorecard/report record in the absorbed tree (project record, not a build/cache artifact), though ignored by the source `.gitignore` pattern `audit_scorecard.json`. |
| `apps/zz-ref-HeliosCLI` | `vendor/` | `.gitignore:16` | 10 | CONTENT | should force-add | Vendored source/build integration files (`codex-rs/vendor/BUILD.bazel` and `codex-rs/vendor/bubblewrap/*` C/meson/docs files) needed by the absorbed component. |
| `apps/zz-ref-HeliosCLI` | `.env.*` | `.gitignore:74` | 1 | CONTENT | should force-add | `deploy/.env.production` is a documented deployment environment template/example with pinned defaults and placeholder credentials (`GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME`); header instructs copying to `.env` and filling values. Inspected content shows no real secrets. |
| `apps/zz-ref-HeliosCLI` | `*.log` | `.gitignore:34` | 2 | ARTIFACT | correctly excluded | Log/output files (`docs/fragemented/.migration.log`, `research/phase-2-reports/agent-a-core-repo-harden/artifacts/clone-fsck.log`) are generated runtime/migration/diagnostic artifacts, not source content. |
| `apps/zz-ref-HeliosCLI` | `worklogs/` | `.gitignore:127` | 5 | CONTENT | should force-add | Project records and documentation (`ARCHITECTURE.md`, `GOVERNANCE.md`, `RESEARCH.md`, `README.md`, and dated worklog JSON `l4-77-helioscli-plugin-arch-2026-06-11.json`), not generated build artifacts. |
| `libs/claude-plugins-official` | `vendor/` | `.gitignore:16` | 2 | CONTENT | must force-add | Vendored plugin asset (`mermaid.min.js`) together with its third-party license notice (`LICENSE-mermaid.txt`); the license file should be preserved with the bundled asset (legal/attribution requirement). |
| `apps/zz-ref-HeliosLite` | `.cargo/` | `apps/zz-ref-HeliosLite/.gitignore:41` | 1 | CONTENT | should force-add | `.cargo/config.toml` contains real build/network configuration (`[net] git-fetch-with-cli = true`) with explanatory rationale for the repo's submodule layout; not machine-local editor state. |
| `apps/zz-ref-HeliosLite` | `audit_scorecard.json` | `.gitignore:117` | 1 | CONTENT | should force-add | Checked-in audit scorecard/report record documenting a specific audited commit, rubric, scores, and gaps; project record rather than build cache/output (present in absorbed tree though ignored by source `.gitignore`). |

## CONTENT Groups (individual paths and sizes)

Paths listed for every CONTENT group (genuinely preservable content).

### `apps/slipstream` — `.env.*` (1 files) — **should force-add**

- Rule source: `.gitignore:74`
- Rationale: `clients/android/.env.template` documents required Android release/build variables with empty placeholders and explicit "DO NOT COMMIT THE .env FILE!" guidance; inspected content shows no secrets.

| Path | Size (bytes) |
| --- | ---: |
| `apps/slipstream/clients/android/.env.template` | 267 |

### `apps/slipstream` — `vendor/` (450 files) — **must force-add**

- Rule source: `.gitignore:16`
- Rationale: Vendored dependency/source/build trees required by the absorbed project (Android NDK crate sources, `pyrowave-sys/vendor/pyrowave` including Granite and bundled third-party code/headers/build files/docs/assets). Vendor trees include embedded third-party license/notice files (e.g. Granite LICENSE, Vulkan headers/volk license files); preserving them is necessary for source completeness, reproducible builds, and license retention.

| Path | Size (bytes) |
| --- | ---: |
| `apps/slipstream/clients/android/native/vendor/ndk/.gitignore` | 30 |
| `apps/slipstream/clients/android/native/vendor/ndk/CHANGELOG.md` | 9192 |
| `apps/slipstream/clients/android/native/vendor/ndk/Cargo.toml` | 2467 |
| `apps/slipstream/clients/android/native/vendor/ndk/README.md` | 2125 |
| `apps/slipstream/clients/android/native/vendor/ndk/README.slipstream.md` | 740 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/asset.rs` | 10306 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/audio.rs` | 60949 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/bitmap.rs` | 18933 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/configuration.rs` | 19777 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/data_space.rs` | 27117 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/event.rs` | 55281 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/font.rs` | 20246 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/hardware_buffer.rs` | 32242 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/hardware_buffer_format.rs` | 5112 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/input_queue.rs` | 5422 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/lib.rs` | 676 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/looper.rs` | 18263 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/image_reader.rs` | 17116 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/media_codec.rs` | 22331 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/media_format.rs` | 8658 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/mod.rs` | 222 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media_error.rs` | 6859 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/native_activity.rs` | 10487 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/native_window.rs` | 20568 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/shared_memory.rs` | 5823 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/surface_texture.rs` | 7950 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/sync.rs` | 4455 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/trace.rs` | 2123 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/utils.rs` | 2791 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/CMakeLists.txt` | 8664 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/.clang-format` | 5959 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/.gitmodules` | 2018 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/CMakeLists.txt` | 15050 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/LICENSE` | 1070 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/OVERVIEW.md` | 29950 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/README.md` | 6992 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/CMakeLists.txt` | 2682 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application.cpp` | 9152 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application.hpp` | 3228 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application_entry.cpp` | 2993 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application_glue.hpp` | 2572 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application_interface_query.cpp` | 72 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/CMakeLists.txt` | 393 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_events.hpp` | 1591 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_wsi.cpp` | 5004 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_wsi.hpp` | 3120 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_wsi_events.hpp` | 5258 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/CMakeLists.txt` | 1248 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers.cpp` | 9065 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers.hpp` | 5915 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers_init.cpp` | 3371 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers_init.hpp` | 1366 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers_interface.hpp` | 3532 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/CMakeLists.txt` | 646 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input.cpp` | 8945 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input.hpp` | 13600 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input_sdl.cpp` | 5941 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input_sdl.hpp` | 1845 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/.dummy.cpp` | 0 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/CMakeLists.txt` | 2392 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/build.gradle` | 541 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/external_layers/README.txt` | 82 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/AndroidManifest.xml` | 1517 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/build.gradle` | 3418 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/gradle.properties` | 25 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-hdpi/icon.png` | 5035 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-mdpi/icon.png` | 2930 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-xhdpi/icon.png` | 8051 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-xxhdpi/icon.png` | 15884 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-xxxhdpi/icon.png` | 26309 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/settings.gradle` | 111 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/settings_custom.gradle` | 194 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/toplevel.build.gradle` | 530 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/src/main/java/net/themaister/granite/GraniteActivity.java` | 5198 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/src/main/res/values/strings.xml` | 25 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/src/main/res/values/themes.xml` | 328 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_android.cpp` | 38671 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_headless.cpp` | 21339 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_headless_wrapper.cpp` | 1457 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_libretro.cpp` | 12087 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_libretro_utils.cpp` | 15290 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_libretro_utils.hpp` | 2758 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_null.cpp` | 1459 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_sdl3.cpp` | 21405 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/libretro/libretro.h` | 215207 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/libretro/libretro_vulkan.h` | 24532 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/scene_viewer_application.cpp` | 58315 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/scene_viewer_application.hpp` | 6087 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/compiler/CMakeLists.txt` | 733 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/compiler/compiler.cpp` | 10503 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/compiler/compiler.hpp` | 3511 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/ecs/CMakeLists.txt` | 183 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/ecs/ecs.cpp` | 3368 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/ecs/ecs.hpp` | 10892 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/event/CMakeLists.txt` | 220 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/event/event.cpp` | 6581 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/event/event.hpp` | 7291 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/CMakeLists.txt` | 1528 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/android/android.cpp` | 3995 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/android/android.hpp` | 2434 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/asset_manager.cpp` | 10922 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/asset_manager.hpp` | 6186 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/filesystem.cpp` | 17909 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/filesystem.hpp` | 8838 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/linux/os_filesystem.cpp` | 12832 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/linux/os_filesystem.hpp` | 3213 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/netfs/fs-netfs.cpp` | 19401 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/netfs/fs-netfs.hpp` | 2896 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/volatile_source.hpp` | 2954 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/windows/os_filesystem.cpp` | 12296 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/windows/os_filesystem.hpp` | 3039 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/CMakeLists.txt` | 438 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/aabb.cpp` | 1725 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/aabb.hpp` | 2304 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/docs/squad.md` | 16834 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/frustum.cpp` | 5084 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/frustum.hpp` | 1633 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/interpolation.cpp` | 1883 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/interpolation.hpp` | 1334 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/math.cpp` | 1375 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/math.hpp` | 1270 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/matrix_helper.hpp` | 2045 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm.cpp` | 11963 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm.hpp` | 23240 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm_impl.hpp` | 40894 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm_test.cpp` | 7082 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/render_parameters.hpp` | 5148 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/simd.hpp` | 24043 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/simd_headers.hpp` | 1622 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/transforms.cpp` | 12074 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/transforms.hpp` | 3136 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/path/CMakeLists.txt` | 201 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/path/path_utils.cpp` | 6693 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/path/path_utils.hpp` | 2096 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/self-test/CMakeLists.txt` | 249 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/self-test/link_test.cpp` | 144 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/CMakeLists.txt` | 6351 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/dirent/dirent.h` | 26801 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.gitattributes` | 594 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/ISSUE_TEMPLATE/bug_report.md` | 1153 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/dependabot.yml` | 232 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/pull_request_template.md` | 560 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/workflows/ci.yml` | 4191 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/BUILD.gn` | 2323 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/BUILD.md` | 1217 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/CMakeLists.txt` | 5918 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/CODE_OF_CONDUCT.adoc` | 369 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/CONTRIBUTING.md` | 1934 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/LICENSE.md` | 458 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/LICENSES/Apache-2.0.txt` | 11358 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/LICENSES/MIT.txt` | 1084 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/Makefile.release` | 4913 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/README.md` | 1919 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/REUSE.toml` | 716 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/SECURITY.md` | 411 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_av1std.h` | 16687 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_av1std_decode.h` | 4250 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_av1std_encode.h` | 5979 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h264std.h` | 13861 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h264std_decode.h` | 2723 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h264std_encode.h` | 6878 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h265std.h` | 23439 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h265std_decode.h` | 2429 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h265std_encode.h` | 7462 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_vp9std.h` | 5384 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_vp9std_decode.h` | 2371 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codecs_common.h` | 660 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vk_icd.h` | 8224 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vk_layer.h` | 7178 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vk_platform.h` | 2828 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan.h` | 1616 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_android.h` | 6330 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_beta.h` | 17412 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_core.h` | 1339147 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_directfb.h` | 1952 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_fuchsia.h` | 12900 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_ggp.h` | 1939 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_ios.h` | 1352 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_macos.h` | 1384 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_metal.h` | 8066 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_ohos.h` | 4106 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_screen.h` | 4193 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_vi.h` | 1325 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_wayland.h` | 1952 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_win32.h` | 15757 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_xcb.h` | 1966 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_xlib.h` | 1947 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_xlib_xrandr.h` | 1497 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/rapidjson_wrapper.hpp` | 1630 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/renderdoc/CMakeLists.txt` | 219 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/renderdoc/renderdoc_app.h` | 28925 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/CMakeLists.txt` | 574 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/stb_image.c` | 125 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/stb_truetype.c` | 63 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/stb_vorbis.h` | 72 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/.github/workflows/build.yml` | 2627 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/.github/workflows/update.yml` | 985 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/CMakeLists.txt` | 4711 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/LICENSE.md` | 1066 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/README.md` | 6807 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/cmake/volkConfig.cmake.in` | 698 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/generate.py` | 7476 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_cpp_namespace/CMakeLists.txt` | 1057 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_cpp_namespace/main.cpp` | 941 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_installed_headers/CMakeLists.txt` | 302 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_installed_headers/main.c` | 1299 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_source_directly/CMakeLists.txt` | 1494 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_source_directly/main.c` | 941 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_headers/CMakeLists.txt` | 386 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_headers/main.c` | 1298 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_static/CMakeLists.txt` | 850 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_static/main.c` | 941 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/run_tests.sh` | 1899 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/volk.c` | 344460 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/volk.h` | 192533 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/CMakeLists.txt` | 341 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/task_composer.cpp` | 2483 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/task_composer.hpp` | 2159 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_group.cpp` | 10414 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_group.hpp` | 6411 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_latch.cpp` | 1898 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_latch.hpp` | 1460 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/toolchains/aarch64.cmake` | 153 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/toolchains/armhf.cmake` | 155 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/CMakeLists.txt` | 1672 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/aligned_alloc.cpp` | 2509 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/aligned_alloc.hpp` | 2104 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/arena_allocator.cpp` | 5424 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/arena_allocator.hpp` | 8938 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/array_view.hpp` | 2063 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/async_object_sink.hpp` | 2707 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/atomic_append_buffer.hpp` | 4777 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/bitops.hpp` | 5239 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/cli_parser.cpp` | 3955 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/cli_parser.hpp` | 2420 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/compile_time_hash.hpp` | 2584 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/dynamic_array.hpp` | 2245 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/dynamic_library.cpp` | 2375 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/dynamic_library.hpp` | 1874 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/enum_cast.hpp` | 1338 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/environment.cpp` | 2457 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/environment.hpp` | 1576 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/generational_handle.hpp` | 4237 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/hash.hpp` | 2256 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/hashmap.hpp` | 1383 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/intrusive.hpp` | 6324 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/intrusive_hash_map.hpp` | 13746 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/intrusive_list.hpp` | 3550 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/logging.cpp` | 2020 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/logging.hpp` | 4733 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/lru_cache.hpp` | 3578 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/message_queue.cpp` | 4977 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/message_queue.hpp` | 6537 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/no_init_pod.hpp` | 1480 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/object_pool.hpp` | 2927 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/radix_sorter.hpp` | 4534 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/read_write_lock.hpp` | 3292 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/slab_allocator.cpp` | 1854 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/slab_allocator.hpp` | 2020 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/small_callable.hpp` | 4343 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/small_vector.hpp` | 10409 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/stack_allocator.hpp` | 1640 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/string_helpers.cpp` | 2338 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/string_helpers.hpp` | 1942 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/temporary_hashmap.hpp` | 3798 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_id.cpp` | 1533 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_id.hpp` | 1252 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_name.cpp` | 1978 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_name.hpp` | 1213 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_priority.cpp` | 2306 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_priority.hpp` | 1278 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timeline_trace_file.cpp` | 4606 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timeline_trace_file.hpp` | 3131 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timer.cpp` | 3570 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timer.hpp` | 1688 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/unordered_array.hpp` | 2896 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/unstable_remove_if.hpp` | 1482 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/variant.hpp` | 1900 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/CMakeLists.txt` | 4893 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/breadcrumbs.cpp` | 18949 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/breadcrumbs.hpp` | 6531 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer.cpp` | 2382 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer.hpp` | 4741 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer_pool.cpp` | 3530 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer_pool.hpp` | 2573 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_buffer.cpp` | 165878 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_buffer.hpp` | 40313 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_pool.cpp` | 5256 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_pool.hpp` | 2025 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/context.cpp` | 83790 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/context.hpp` | 17143 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/cookie.cpp` | 1273 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/cookie.hpp` | 1611 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/descriptor_set.cpp` | 21782 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/descriptor_set.hpp` | 7006 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device.cpp` | 192431 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device.hpp` | 41139 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device_fossilize.cpp` | 40032 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device_fossilize.hpp` | 2380 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/event_manager.cpp` | 2151 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/event_manager.hpp` | 1540 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence.cpp` | 4546 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence.hpp` | 2322 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence_manager.cpp` | 1837 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence_manager.hpp` | 1487 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/format.hpp` | 10963 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/image.cpp` | 6757 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/image.hpp` | 16176 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/indirect_layout.cpp` | 5692 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/indirect_layout.hpp` | 2172 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/limits.hpp` | 1936 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/resource_manager.cpp` | 29339 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/resource_manager.hpp` | 6257 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/shader_manager.cpp` | 33584 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/shader_manager.hpp` | 8824 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/memory_allocator.cpp` | 53833 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/memory_allocator.hpp` | 13303 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/mesh/meshlet.cpp` | 9310 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/mesh/meshlet.hpp` | 3688 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_cache.cpp` | 22331 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_cache.hpp` | 3553 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_event.cpp` | 1473 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_event.hpp` | 1888 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/CMakeLists.txt` | 1097 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/NsightAftermathGpuCrashTracker.cpp` | 16705 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/NsightAftermathGpuCrashTracker.h` | 6333 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/NsightAftermathHelpers.h` | 5673 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/post_mortem.cpp` | 2148 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/post_mortem.hpp` | 1305 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/query_pool.cpp` | 16007 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/query_pool.hpp` | 5392 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/quirks.hpp` | 1830 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/render_pass.cpp` | 37301 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/render_pass.hpp` | 7817 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/renderdoc_capture.cpp` | 3475 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/rtas.cpp` | 2057 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/rtas.hpp` | 3025 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/sampler.cpp` | 6227 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/sampler.hpp` | 4193 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore.cpp` | 7089 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore.hpp` | 5157 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore_manager.cpp` | 2040 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore_manager.hpp` | 1513 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/shader.cpp` | 41433 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/shader.hpp` | 10334 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/memory_mapped_texture.cpp` | 10038 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/memory_mapped_texture.hpp` | 3304 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_decoder.cpp` | 39553 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_decoder.hpp` | 1850 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_files.cpp` | 3938 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_files.hpp` | 1600 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_format.cpp` | 13632 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_format.hpp` | 5557 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/type_to_string.hpp` | 3759 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/vulkan_common.hpp` | 4860 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/vulkan_headers.hpp` | 2356 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/vulkan_prerotate.hpp` | 4599 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi.cpp` | 99107 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi.hpp` | 18733 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_dxgi.cpp` | 15972 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_dxgi.hpp` | 2744 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_pacer.cpp` | 11134 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_pacer.hpp` | 3341 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/LICENSE` | 1065 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/README.md` | 3949 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/SLIPSTREAM-VENDOR.txt` | 3156 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/bench.cpp` | 8570 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/bitstream/bitstream.md` | 19019 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/build-steamrt-helper.sh` | 297 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/build-steamrt.sh` | 149 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/build_aarch64.sh` | 564 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/checkout_granite.sh` | 466 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/com_ptr.hpp` | 1498 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/decode.cpp` | 7585 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/encode.cpp` | 7852 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/link.T` | 39 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/metrics/plot.py` | 1852 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/metrics/triage.sh` | 4769 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pkg-config/pyrowave-shared.pc.in` | 353 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/psnr.cpp` | 3255 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave-shared.def` | 1143 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave.h` | 24549 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_c.cpp` | 51066 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_c_interop_test.cpp` | 72278 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_c_test.cpp` | 18577 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_common.cpp` | 9469 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_common.hpp` | 4651 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_config.hpp` | 271 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_decoder.cpp` | 31669 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_decoder.hpp` | 1259 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_device_validation.cpp` | 7727 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_encoder.cpp` | 42812 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_encoder.hpp` | 1373 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/sandbox.cpp` | 11412 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/setup_android_build.sh` | 387 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/analyze_rate_control.comp` | 7071 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/analyze_rate_control_finalize.comp` | 882 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/block_packing.comp` | 12529 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/constants.h` | 179 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt.comp` | 8179 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt_common.h` | 1520 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt_quant_scale.h` | 469 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt_swizzle.h` | 526 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/idwt.comp` | 7981 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/idwt.frag` | 7396 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/idwt.vert` | 651 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/power_to_db.comp` | 924 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/resolve_rate_control.comp` | 2563 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/slangmosh.hpp` | 821355 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/slangmosh.json` | 1365 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/wavelet_dequant.comp` | 11615 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/wavelet_quant.comp` | 10834 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/yuv2rgb.frag` | 1655 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/slangmosh.sh` | 109 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/viewer.cpp` | 18295 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/yuv4mpeg.cpp` | 5352 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/yuv4mpeg.hpp` | 1209 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/Cargo.toml` | 460 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/LICENSE` | 1300 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/README.md` | 2442 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/build.rs` | 6025 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/errors.rs` | 2066 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/galois.rs` | 21869 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/lib.rs` | 2529 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/matrix.rs` | 7222 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/reed_solomon.rs` | 42308 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/Cargo.toml` | 1501 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/LICENSE-MIT` | 1073 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/NOTICE` | 1205 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/consts.rs` | 3011 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/device.rs` | 26365 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/endpoint.rs` | 701 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/interface.rs` | 1408 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/lib.rs` | 8931 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/setup.rs` | 860 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/usbip_protocol.rs` | 17569 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/util.rs` | 302 |
| `apps/slipstream/web/vendor/unom-style/package.json` | 135 |
| `apps/slipstream/web/vendor/unom-style/src/index.ts` | 220 |
| `apps/slipstream/web/vendor/unom-ui/package.json` | 502 |
| `apps/slipstream/web/vendor/unom-ui/src/button.tsx` | 1915 |
| `apps/slipstream/web/vendor/unom-ui/src/card.tsx` | 627 |
| `apps/slipstream/web/vendor/unom-ui/src/dialog.tsx` | 3424 |
| `apps/slipstream/web/vendor/unom-ui/src/form/checkbox.tsx` | 1234 |
| `apps/slipstream/web/vendor/unom-ui/src/form/input-text.tsx` | 587 |
| `apps/slipstream/web/vendor/unom-ui/src/form/label.tsx` | 405 |
| `apps/slipstream/web/vendor/unom-ui/src/material.tsx` | 195 |
| `apps/slipstream/web/vendor/unom-ui/src/section.tsx` | 322 |
| `apps/slipstream/web/vendor/unom-ui/src/tabs.tsx` | 2039 |
| `apps/slipstream/web/vendor/unom-ui/src/toast.tsx` | 1427 |

### `apps/zz-ref-HeliosCLI` — `.codex/` (24 files) — **should force-add**

- Rule source: `.gitignore:80`
- Rationale: Repo-shipped Codex environment configuration and skill definitions, agents metadata, references, scripts, and tests under `.codex/`; project tooling/content rather than transient editor cache.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/.codex/environments/environment.toml` | 287 |
| `apps/zz-ref-HeliosCLI/.codex/environments/setup.py` | 2050 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/SKILL.md` | 16861 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/agents/openai.yaml` | 1416 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/references/github-api-notes.md` | 2343 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/references/heuristics.md` | 3308 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/scripts/gh_pr_watch.py` | 29438 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/scripts/test_gh_pr_watch.py` | 8094 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-breaking-changes/SKILL.md` | 324 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-change-size/SKILL.md` | 467 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-context/SKILL.md` | 661 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-testing/SKILL.md` | 604 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review/SKILL.md` | 671 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-bug/SKILL.md` | 2573 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/SKILL.md` | 9336 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/agents/openai.yaml` | 243 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/scripts/collect_issue_digest.py` | 34363 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/scripts/test_collect_issue_digest.py` | 24592 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-pr-body/SKILL.md` | 4447 |
| `apps/zz-ref-HeliosCLI/.codex/skills/path-types/SKILL.md` | 2424 |
| `apps/zz-ref-HeliosCLI/.codex/skills/pushing-ci-changes/SKILL.md` | 894 |
| `apps/zz-ref-HeliosCLI/.codex/skills/remote-tests/SKILL.md` | 3367 |
| `apps/zz-ref-HeliosCLI/.codex/skills/update-v8-version/SKILL.md` | 3378 |
| `apps/zz-ref-HeliosCLI/.codex/skills/update-v8-version/agents/openai.yaml` | 228 |

### `apps/zz-ref-HeliosCLI` — `audit_scorecard.json` (1 files) — **should force-add**

- Rule source: `.gitignore:117`
- Rationale: `audit_scorecard.json` is a checked-in audit scorecard/report record in the absorbed tree (project record, not a build/cache artifact), though ignored by the source `.gitignore` pattern `audit_scorecard.json`.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/audit_scorecard.json` | 212 |

### `apps/zz-ref-HeliosCLI` — `vendor/` (10 files) — **should force-add**

- Rule source: `.gitignore:16`
- Rationale: Vendored source/build integration files (`codex-rs/vendor/BUILD.bazel` and `codex-rs/vendor/bubblewrap/*` C/meson/docs files) needed by the absorbed component.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/BUILD.bazel` | 426 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/NEWS.md` | 3137 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/README.md` | 11238 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/SECURITY.md` | 2375 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/bubblewrap.c` | 117032 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/meson.build` | 4613 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/meson_options.txt` | 1673 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/network.c` | 5429 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/release-checklist.md` | 777 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/utils.c` | 21879 |

### `apps/zz-ref-HeliosCLI` — `.env.*` (1 files) — **should force-add**

- Rule source: `.gitignore:74`
- Rationale: `deploy/.env.production` is a documented deployment environment template/example with pinned defaults and placeholder credentials (`GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME`); header instructs copying to `.env` and filling values. Inspected content shows no real secrets.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/deploy/.env.production` | 3385 |

### `apps/zz-ref-HeliosCLI` — `worklogs/` (5 files) — **should force-add**

- Rule source: `.gitignore:127`
- Rationale: Project records and documentation (`ARCHITECTURE.md`, `GOVERNANCE.md`, `RESEARCH.md`, `README.md`, and dated worklog JSON `l4-77-helioscli-plugin-arch-2026-06-11.json`), not generated build artifacts.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/worklogs/ARCHITECTURE.md` | 127 |
| `apps/zz-ref-HeliosCLI/worklogs/GOVERNANCE.md` | 118 |
| `apps/zz-ref-HeliosCLI/worklogs/README.md` | 658 |
| `apps/zz-ref-HeliosCLI/worklogs/RESEARCH.md` | 126 |
| `apps/zz-ref-HeliosCLI/worklogs/l4-77-helioscli-plugin-arch-2026-06-11.json` | 4988 |

### `libs/claude-plugins-official` — `vendor/` (2 files) — **must force-add**

- Rule source: `.gitignore:16`
- Rationale: Vendored plugin asset (`mermaid.min.js`) together with its third-party license notice (`LICENSE-mermaid.txt`); the license file should be preserved with the bundled asset (legal/attribution requirement).

| Path | Size (bytes) |
| --- | ---: |
| `libs/claude-plugins-official/plugins/code-modernization/assets/vendor/LICENSE-mermaid.txt` | 1746 |
| `libs/claude-plugins-official/plugins/code-modernization/assets/vendor/mermaid.min.js` | 3572661 |

### `apps/zz-ref-HeliosLite` — `.cargo/` (1 files) — **should force-add**

- Rule source: `apps/zz-ref-HeliosLite/.gitignore:41`
- Rationale: `.cargo/config.toml` contains real build/network configuration (`[net] git-fetch-with-cli = true`) with explanatory rationale for the repo's submodule layout; not machine-local editor state.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosLite/.cargo/config.toml` | 192 |

### `apps/zz-ref-HeliosLite` — `audit_scorecard.json` (1 files) — **should force-add**

- Rule source: `.gitignore:117`
- Rationale: Checked-in audit scorecard/report record documenting a specific audited commit, rubric, scores, and gaps; project record rather than build cache/output (present in absorbed tree though ignored by source `.gitignore`).

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosLite/audit_scorecard.json` | 1793 |

## ARTIFACT Groups (correctly excluded)

### `apps/slipstream` — `.vscode/` (1 files) — **correctly excluded**

- Rule source: `.gitignore:23`
- Rationale: Editor/IDE launch configuration (`.vscode/launch.json`), machine-local/editor state; not required project source/content.

| Path | Size (bytes) |
| --- | ---: |
| `apps/slipstream/.vscode/launch.json` | 834 |

### `apps/zz-ref-HeliosCLI` — `coverage/` (9 files) — **correctly excluded**

- Rule source: `.gitignore:38`
- Rationale: Generated test/coverage/lint output and summary logs under `artifacts/coverage/` (build/test artifacts), not source records.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/after-summary-new.txt` | 32532 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/after-summary.txt` | 36519 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/before-summary.txt` | 27584 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/clippy-final.log` | 9898 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/clippy.log` | 9846 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/metrics.json` | 1200 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/workspace-test-final.log` | 32242 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/workspace-test-verify.log` | 22250 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/workspace-test.log` | 30701 |

### `apps/zz-ref-HeliosCLI` — `tmp-*` (1 files) — **correctly excluded**

- Rule source: `.gitignore:91`
- Rationale: Temporary discovery output (`artifacts/phase-2/tmp-discovery-opencode.json`).

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/artifacts/phase-2/tmp-discovery-opencode.json` | 8345 |

### `apps/zz-ref-HeliosCLI` — `*.log` (2 files) — **correctly excluded**

- Rule source: `.gitignore:34`
- Rationale: Log/output files (`docs/fragemented/.migration.log`, `research/phase-2-reports/agent-a-core-repo-harden/artifacts/clone-fsck.log`) are generated runtime/migration/diagnostic artifacts, not source content.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/docs/fragemented/.migration.log` | 6291 |
| `apps/zz-ref-HeliosCLI/research/phase-2-reports/agent-a-core-repo-harden/artifacts/clone-fsck.log` | 109 |

## Exact `git add -f` commands to recover only genuinely lost files

Run from `C:\Users\koosh\PhenoShared`. These commands target only groups classified as **CONTENT** (genuinely lost/preservable); **ARTIFACT** groups are intentionally excluded. No commit/push implied; `git add -f` was **not** executed.

```bat
git add -f -- "apps/slipstream/clients/android/.env.template"
git add -f -- "apps/slipstream/clients/android/native/vendor"
git add -f -- "apps/slipstream/crates/pyrowave-sys/vendor"
git add -f -- "apps/slipstream/crates/slipstream-core/vendor"
git add -f -- "apps/slipstream/crates/slipstream-host/vendor"
git add -f -- "apps/slipstream/web/vendor"
git add -f -- "apps/zz-ref-HeliosCLI/.codex"
git add -f -- "apps/zz-ref-HeliosCLI/audit_scorecard.json"
git add -f -- "apps/zz-ref-HeliosCLI/codex-rs/vendor"
git add -f -- "apps/zz-ref-HeliosCLI/deploy/.env.production"
git add -f -- "apps/zz-ref-HeliosCLI/worklogs"
git add -f -- "libs/claude-plugins-official/plugins/code-modernization/assets/vendor"
git add -f -- "apps/zz-ref-HeliosLite/.cargo/config.toml"
git add -f -- "apps/zz-ref-HeliosLite/audit_scorecard.json"
```

Notes:
- Recovery commands are limited to CONTENT groups: vendored sources/assets and embedded license/notice files, repo-shipped `.codex/` skills/config, worklog/project-record files, config/template files (`.env.template`, `deploy/.env.production`, `.cargo/config.toml`), and `audit_scorecard.json` files.
- Excluded as ARTIFACT (correctly left out): `apps/slipstream/.vscode/launch.json`, `apps/zz-ref-HeliosCLI/artifacts/coverage/*` (9 files), `apps/zz-ref-HeliosCLI/artifacts/phase-2/tmp-discovery-opencode.json`, and `apps/zz-ref-HeliosCLI` `*.log` files (2).
- **Genuinely lost files (recoverable CONTENT): 496**. Correctly excluded ARTIFACT files: 13.
