# Absorption Exclusions Ledger (2026-11-19)

Read-only classification of files present in absorbed working trees but omitted from commit because `git add` obeyed `.gitignore`.

**Method:** `python3 -u scripts/check_ignored.py apps/slipstream apps/zz-ref-HeliosCLI libs/claude-plugins-official apps/zz-ref-HeliosLite` plus per-file rule/size enumeration via `git ls-files --others --ignored --exclude-standard` and `git check-ignore -v --no-index --stdin` (no git state changes; no `git add -f` run).

- Total ignored/missing files analyzed: **506**
- Distinct rule groups: **12**
- Genuinely lost (CONTENT, should be preserved): **495**
- Correctly excluded (ARTIFACT): **11**

## Rule Group Classification

| Repo | Rule | Source | Count | Classification | Recommendation | Notes |
| --- | --- | --- | ---: | --- | --- | --- |
| `apps/slipstream` | `.vscode/` | `.gitignore:23` | 1 | ARTIFACT | correctly excluded | Editor/IDE launch configuration (machine-local/editor state), not required project source/content. |
| `apps/slipstream` | `.env.*` | `.gitignore:74` | 1 | CONTENT | should force-add | `clients/android/.env.template` documents required Android release/build variables with empty placeholders and explicit "DO NOT COMMIT THE .env FILE!" guidance; inspected content shows no secrets. |
| `apps/slipstream` | `vendor/` | `.gitignore:16` | 450 | CONTENT | must force-add | Vendored dependency/source/build trees required by the absorbed project (Android NDK crate sources, pyrowave-sys/Granite and bundled third-party code/headers/build files/docs/assets). Vendor trees include embedded third-party license/notice files; preserving them is necessary for source completeness, reproducible builds, and license retention. |
| `apps/zz-ref-HeliosCLI` | `.codex/` | `.gitignore:80` | 24 | CONTENT | should force-add | Repo-shipped Codex environment configuration and skill definitions, references, scripts, and tests under `.codex/`; project tooling/content rather than transient editor cache. |
| `apps/zz-ref-HeliosCLI` | `coverage/` | `.gitignore:38` | 9 | ARTIFACT | correctly excluded | Generated test/coverage/lint output and summary logs under `artifacts/coverage/` (build/test artifacts). |
| `apps/zz-ref-HeliosCLI` | `tmp-*` | `.gitignore:91` | 1 | ARTIFACT | correctly excluded | Temporary discovery output (`artifacts/phase-2/tmp-discovery-opencode.json`). |
| `apps/zz-ref-HeliosCLI` | `vendor/` | `.gitignore:16` | 10 | CONTENT | should force-add | Vendored source/build integration files (`codex-rs/vendor/BUILD.bazel` and bubblewrap C/meson/docs files) needed by the absorbed component. |
| `apps/zz-ref-HeliosCLI` | `.env.*` | `.gitignore:74` | 1 | CONTENT | should force-add | `deploy/.env.production` is a documented deployment environment template/example with pinned defaults and placeholder credentials (`GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME`); header instructs copying to `.env` and filling values. Inspected content shows no real secrets. |
| `apps/zz-ref-HeliosCLI` | `worklogs/` | `.gitignore:127` | 5 | CONTENT | should force-add | Project records and documentation (`ARCHITECTURE.md`, `GOVERNANCE.md`, `RESEARCH.md`, `README.md`, and dated worklog JSON), not generated build artifacts. |
| `libs/claude-plugins-official` | `vendor/` | `.gitignore:16` | 2 | CONTENT | must force-add | Vendored plugin asset (`mermaid.min.js`) together with its third-party license notice (`LICENSE-mermaid.txt`); the license file should be preserved with the bundled asset. |
| `apps/zz-ref-HeliosLite` | `.cargo/` | `apps/zz-ref-HeliosLite/.gitignore:41` | 1 | CONTENT | should force-add | `.cargo/config.toml` contains real build/network configuration (`[net] git-fetch-with-cli = true`) with explanatory rationale; not machine-local editor state. |
| `apps/zz-ref-HeliosLite` | `audit_scorecard.json` | `.gitignore:117` | 1 | CONTENT | should force-add | Checked-in audit scorecard/report record documenting a specific audited commit, rubric, scores, and gaps; project record rather than build cache/output (present in absorbed tree though ignored by source `.gitignore`). |

## CONTENT Groups (individual paths and sizes)

### `apps/slipstream` — `.env.*` (1 files) — **should force-add**

- Rule source: `.gitignore:74`
- Rationale: `clients/android/.env.template` documents required Android release/build variables with empty placeholders and explicit "DO NOT COMMIT THE .env FILE!" guidance; inspected content shows no secrets.

| Path | Size (bytes) |
| --- | ---: |
| `apps/slipstream/clients/android/.env.template/r` | -1 |

### `apps/slipstream` — `vendor/` (450 files) — **must force-add**

- Rule source: `.gitignore:16`
- Rationale: Vendored dependency/source/build trees required by the absorbed project (Android NDK crate sources, pyrowave-sys/Granite and bundled third-party code/headers/build files/docs/assets). Vendor trees include embedded third-party license/notice files; preserving them is necessary for source completeness, reproducible builds, and license retention.

| Path | Size (bytes) |
| --- | ---: |
| `apps/slipstream/clients/android/native/vendor/ndk/.gitignore/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/CHANGELOG.md/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/Cargo.toml/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/README.md/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/README.slipstream.md/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/asset.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/audio.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/bitmap.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/configuration.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/data_space.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/event.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/font.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/hardware_buffer.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/hardware_buffer_format.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/input_queue.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/lib.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/looper.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/image_reader.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/media_codec.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/media_format.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media/mod.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/media_error.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/native_activity.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/native_window.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/shared_memory.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/surface_texture.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/sync.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/trace.rs/r` | -1 |
| `apps/slipstream/clients/android/native/vendor/ndk/src/utils.rs/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/.clang-format/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/.gitmodules/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/LICENSE/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/OVERVIEW.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/README.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application_entry.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application_glue.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/application_interface_query.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_events.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_wsi.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_wsi.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/events/application_wsi_events.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers_init.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers_init.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/global/global_managers_interface.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input_sdl.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/input/input_sdl.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/.dummy.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/build.gradle/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/external_layers/README.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/AndroidManifest.xml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/build.gradle/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/gradle.properties/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-hdpi/icon.png/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-mdpi/icon.png/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-xhdpi/icon.png/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-xxhdpi/icon.png/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/res/drawable-xxxhdpi/icon.png/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/settings.gradle/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/settings_custom.gradle/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/gradle/toplevel.build.gradle/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/src/main/java/net/themaister/granite/GraniteActivity.java/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/src/main/res/values/strings.xml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/android/src/main/res/values/themes.xml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_android.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_headless.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_headless_wrapper.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_libretro.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_libretro_utils.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_libretro_utils.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_null.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/application_sdl3.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/libretro/libretro.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/platforms/libretro/libretro_vulkan.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/scene_viewer_application.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/application/scene_viewer_application.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/compiler/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/compiler/compiler.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/compiler/compiler.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/ecs/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/ecs/ecs.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/ecs/ecs.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/event/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/event/event.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/event/event.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/android/android.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/android/android.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/asset_manager.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/asset_manager.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/filesystem.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/filesystem.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/linux/os_filesystem.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/linux/os_filesystem.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/netfs/fs-netfs.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/netfs/fs-netfs.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/volatile_source.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/windows/os_filesystem.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/filesystem/windows/os_filesystem.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/aabb.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/aabb.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/docs/squad.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/frustum.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/frustum.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/interpolation.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/interpolation.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/math.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/math.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/matrix_helper.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm_impl.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/muglm/muglm_test.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/render_parameters.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/simd.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/simd_headers.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/transforms.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/math/transforms.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/path/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/path/path_utils.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/path/path_utils.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/self-test/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/self-test/link_test.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/dirent/dirent.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.gitattributes/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/ISSUE_TEMPLATE/bug_report.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/dependabot.yml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/pull_request_template.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/.github/workflows/ci.yml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/BUILD.gn/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/BUILD.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/CODE_OF_CONDUCT.adoc/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/CONTRIBUTING.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/LICENSE.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/LICENSES/Apache-2.0.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/LICENSES/MIT.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/Makefile.release/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/README.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/REUSE.toml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/SECURITY.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_av1std.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_av1std_decode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_av1std_encode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h264std.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h264std_decode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h264std_encode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h265std.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h265std_decode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_h265std_encode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_vp9std.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codec_vp9std_decode.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vk_video/vulkan_video_codecs_common.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vk_icd.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vk_layer.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vk_platform.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_android.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_beta.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_core.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_directfb.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_fuchsia.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_ggp.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_ios.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_macos.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_metal.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_ohos.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_screen.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_vi.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_wayland.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_win32.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_xcb.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_xlib.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/khronos/vulkan-headers/include/vulkan/vulkan_xlib_xrandr.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/rapidjson_wrapper.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/renderdoc/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/renderdoc/renderdoc_app.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/stb_image.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/stb_truetype.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/stb/stb_vorbis.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/.github/workflows/build.yml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/.github/workflows/update.yml/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/LICENSE.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/README.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/cmake/volkConfig.cmake.in/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/generate.py/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_cpp_namespace/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_cpp_namespace/main.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_installed_headers/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_installed_headers/main.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_source_directly/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_source_directly/main.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_headers/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_headers/main.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_static/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/cmake_using_subdir_static/main.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/test/run_tests.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/volk.c/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/third_party/volk/volk.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/task_composer.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/task_composer.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_group.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_group.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_latch.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/threading/thread_latch.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/toolchains/aarch64.cmake/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/toolchains/armhf.cmake/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/aligned_alloc.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/aligned_alloc.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/arena_allocator.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/arena_allocator.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/array_view.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/async_object_sink.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/atomic_append_buffer.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/bitops.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/cli_parser.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/cli_parser.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/compile_time_hash.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/dynamic_array.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/dynamic_library.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/dynamic_library.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/enum_cast.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/environment.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/environment.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/generational_handle.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/hash.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/hashmap.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/intrusive.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/intrusive_hash_map.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/intrusive_list.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/logging.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/logging.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/lru_cache.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/message_queue.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/message_queue.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/no_init_pod.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/object_pool.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/radix_sorter.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/read_write_lock.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/slab_allocator.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/slab_allocator.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/small_callable.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/small_vector.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/stack_allocator.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/string_helpers.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/string_helpers.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/temporary_hashmap.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_id.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_id.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_name.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_name.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_priority.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/thread_priority.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timeline_trace_file.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timeline_trace_file.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timer.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/timer.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/unordered_array.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/unstable_remove_if.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/util/variant.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/breadcrumbs.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/breadcrumbs.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer_pool.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/buffer_pool.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_buffer.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_buffer.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_pool.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/command_pool.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/context.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/context.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/cookie.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/cookie.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/descriptor_set.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/descriptor_set.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device_fossilize.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/device_fossilize.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/event_manager.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/event_manager.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence_manager.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/fence_manager.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/format.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/image.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/image.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/indirect_layout.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/indirect_layout.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/limits.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/resource_manager.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/resource_manager.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/shader_manager.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/managers/shader_manager.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/memory_allocator.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/memory_allocator.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/mesh/meshlet.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/mesh/meshlet.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_cache.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_cache.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_event.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/pipeline_event.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/CMakeLists.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/NsightAftermathGpuCrashTracker.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/NsightAftermathGpuCrashTracker.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/NsightAftermathHelpers.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/post_mortem.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/post-mortem/post_mortem.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/query_pool.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/query_pool.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/quirks.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/render_pass.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/render_pass.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/renderdoc_capture.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/rtas.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/rtas.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/sampler.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/sampler.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore_manager.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/semaphore_manager.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/shader.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/shader.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/memory_mapped_texture.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/memory_mapped_texture.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_decoder.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_decoder.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_files.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_files.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_format.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/texture/texture_format.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/type_to_string.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/vulkan_common.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/vulkan_headers.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/vulkan_prerotate.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_dxgi.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_dxgi.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_pacer.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/Granite/vulkan/wsi_pacer.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/LICENSE/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/README.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/SLIPSTREAM-VENDOR.txt/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/bench.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/bitstream/bitstream.md/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/build-steamrt-helper.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/build-steamrt.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/build_aarch64.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/checkout_granite.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/com_ptr.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/decode.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/encode.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/link.T/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/metrics/plot.py/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/metrics/triage.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pkg-config/pyrowave-shared.pc.in/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/psnr.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave-shared.def/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_c.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_c_interop_test.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_c_test.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_common.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_common.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_config.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_decoder.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_decoder.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_device_validation.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_encoder.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/pyrowave_encoder.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/sandbox.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/setup_android_build.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/analyze_rate_control.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/analyze_rate_control_finalize.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/block_packing.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/constants.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt_common.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt_quant_scale.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/dwt_swizzle.h/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/idwt.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/idwt.frag/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/idwt.vert/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/power_to_db.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/resolve_rate_control.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/slangmosh.hpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/slangmosh.json/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/wavelet_dequant.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/wavelet_quant.comp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/shaders/yuv2rgb.frag/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/slangmosh.sh/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/viewer.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/yuv4mpeg.cpp/r` | -1 |
| `apps/slipstream/crates/pyrowave-sys/vendor/pyrowave/yuv4mpeg.hpp/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/Cargo.toml/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/LICENSE/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/README.md/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/build.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/errors.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/galois.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/lib.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/matrix.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-core/vendor/fec-rs/src/reed_solomon.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/Cargo.toml/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/LICENSE-MIT/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/NOTICE/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/consts.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/device.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/endpoint.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/interface.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/lib.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/setup.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/usbip_protocol.rs/r` | -1 |
| `apps/slipstream/crates/slipstream-host/vendor/usbip-sim/src/util.rs/r` | -1 |
| `apps/slipstream/web/vendor/unom-style/package.json/r` | -1 |
| `apps/slipstream/web/vendor/unom-style/src/index.ts/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/package.json/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/button.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/card.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/dialog.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/form/checkbox.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/form/input-text.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/form/label.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/material.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/section.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/tabs.tsx/r` | -1 |
| `apps/slipstream/web/vendor/unom-ui/src/toast.tsx` | 1427 |

### `apps/zz-ref-HeliosCLI` — `.codex/` (24 files) — **should force-add**

- Rule source: `.gitignore:80`
- Rationale: Repo-shipped Codex environment configuration and skill definitions, references, scripts, and tests under `.codex/`; project tooling/content rather than transient editor cache.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/.codex/environments/environment.toml/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/environments/setup.py/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/agents/openai.yaml/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/references/github-api-notes.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/references/heuristics.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/scripts/gh_pr_watch.py/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/babysit-pr/scripts/test_gh_pr_watch.py/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-breaking-changes/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-change-size/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-context/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review-testing/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/code-review/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-bug/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/agents/openai.yaml/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/scripts/collect_issue_digest.py/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-issue-digest/scripts/test_collect_issue_digest.py/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/codex-pr-body/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/path-types/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/pushing-ci-changes/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/remote-tests/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/update-v8-version/SKILL.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/.codex/skills/update-v8-version/agents/openai.yaml/r` | -1 |

### `apps/zz-ref-HeliosCLI` — `vendor/` (10 files) — **should force-add**

- Rule source: `.gitignore:16`
- Rationale: Vendored source/build integration files (`codex-rs/vendor/BUILD.bazel` and bubblewrap C/meson/docs files) needed by the absorbed component.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/BUILD.bazel/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/NEWS.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/README.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/SECURITY.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/bubblewrap.c/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/meson.build/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/meson_options.txt/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/network.c/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/release-checklist.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/codex-rs/vendor/bubblewrap/utils.c/r` | -1 |

### `apps/zz-ref-HeliosCLI` — `.env.*` (1 files) — **should force-add**

- Rule source: `.gitignore:74`
- Rationale: `deploy/.env.production` is a documented deployment environment template/example with pinned defaults and placeholder credentials (`GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME`); header instructs copying to `.env` and filling values. Inspected content shows no real secrets.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/deploy/.env.production/r` | -1 |

### `apps/zz-ref-HeliosCLI` — `worklogs/` (5 files) — **should force-add**

- Rule source: `.gitignore:127`
- Rationale: Project records and documentation (`ARCHITECTURE.md`, `GOVERNANCE.md`, `RESEARCH.md`, `README.md`, and dated worklog JSON), not generated build artifacts.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/worklogs/ARCHITECTURE.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/worklogs/GOVERNANCE.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/worklogs/README.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/worklogs/RESEARCH.md/r` | -1 |
| `apps/zz-ref-HeliosCLI/worklogs/l4-77-helioscli-plugin-arch-2026-06-11.json` | 4988 |

### `libs/claude-plugins-official` — `vendor/` (2 files) — **must force-add**

- Rule source: `.gitignore:16`
- Rationale: Vendored plugin asset (`mermaid.min.js`) together with its third-party license notice (`LICENSE-mermaid.txt`); the license file should be preserved with the bundled asset.

| Path | Size (bytes) |
| --- | ---: |
| `libs/claude-plugins-official/plugins/code-modernization/assets/vendor/LICENSE-mermaid.txt/r` | -1 |
| `libs/claude-plugins-official/plugins/code-modernization/assets/vendor/mermaid.min.js` | 3572661 |

### `apps/zz-ref-HeliosLite` — `.cargo/` (1 files) — **should force-add**

- Rule source: `apps/zz-ref-HeliosLite/.gitignore:41`
- Rationale: `.cargo/config.toml` contains real build/network configuration (`[net] git-fetch-with-cli = true`) with explanatory rationale; not machine-local editor state.

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosLite/.cargo/config.toml/r` | -1 |

### `apps/zz-ref-HeliosLite` — `audit_scorecard.json` (1 files) — **should force-add**

- Rule source: `.gitignore:117`
- Rationale: Checked-in audit scorecard/report record documenting a specific audited commit, rubric, scores, and gaps; project record rather than build cache/output (present in absorbed tree though ignored by source `.gitignore`).

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosLite/audit_scorecard.json` | 1793 |

## ARTIFACT Groups (correctly excluded)

### `apps/slipstream` — `.vscode/` (1 files) — **correctly excluded**

- Rule source: `.gitignore:23`
- Rationale: Editor/IDE launch configuration (machine-local/editor state), not required project source/content.

| Path | Size (bytes) |
| --- | ---: |
| `apps/slipstream/.vscode/launch.json/r` | -1 |

### `apps/zz-ref-HeliosCLI` — `coverage/` (9 files) — **correctly excluded**

- Rule source: `.gitignore:38`
- Rationale: Generated test/coverage/lint output and summary logs under `artifacts/coverage/` (build/test artifacts).

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/after-summary-new.txt/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/after-summary.txt/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/before-summary.txt/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/clippy-final.log/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/clippy.log/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/metrics.json/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/workspace-test-final.log/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/workspace-test-verify.log/r` | -1 |
| `apps/zz-ref-HeliosCLI/artifacts/coverage/workspace-test.log/r` | -1 |

### `apps/zz-ref-HeliosCLI` — `tmp-*` (1 files) — **correctly excluded**

- Rule source: `.gitignore:91`
- Rationale: Temporary discovery output (`artifacts/phase-2/tmp-discovery-opencode.json`).

| Path | Size (bytes) |
| --- | ---: |
| `apps/zz-ref-HeliosCLI/artifacts/phase-2/tmp-discovery-opencode.json/r` | -1 |

## Exact `git add -f` commands to recover only genuinely lost files

Run from `C:\Users\koosh\PhenoShared`. These commands target only groups classified as **CONTENT** (genuinely lost/preservable); **ARTIFACT** groups are intentionally excluded. No commit/push implied; `git add -f` was **not** executed.

```bat
git add -f -- "apps/slipstream/clients/android/.env.template/r"
git add -f -- "apps/slipstream/clients/android/native/vendor"
git add -f -- "apps/slipstream/crates/pyrowave-sys/vendor"
git add -f -- "apps/slipstream/crates/slipstream-core/vendor"
git add -f -- "apps/slipstream/crates/slipstream-host/vendor"
git add -f -- "apps/slipstream/web/vendor"
git add -f -- "apps/zz-ref-HeliosCLI/.codex"
git add -f -- "apps/zz-ref-HeliosCLI/codex-rs/vendor"
git add -f -- "apps/zz-ref-HeliosCLI/deploy/.env.production/r"
git add -f -- "apps/zz-ref-HeliosCLI/worklogs"
git add -f -- "libs/claude-plugins-official/plugins/code-modernization/assets/vendor"
git add -f -- "apps/zz-ref-HeliosLite/.cargo/config.toml"
git add -f -- "apps/zz-ref-HeliosLite/audit_scorecard.json"
```

Notes:
- Recovery commands are limited to CONTENT groups: vendored sources/assets and embedded license files, repo-shipped `.codex/` skills/config, worklog records, config/template files (`.env.template`, `deploy/.env.production`, `.cargo/config.toml`), and `audit_scorecard.json`.
- Excluded as ARTIFACT (correctly left out): `apps/slipstream/.vscode/launch.json`, `apps/zz-ref-HeliosCLI/artifacts/coverage/*` (9 files), and `apps/zz-ref-HeliosCLI/artifacts/phase-2/tmp-discovery-opencode.json`.
- **Genuinely lost files (recoverable CONTENT): 495**. Correctly excluded ARTIFACT files: 11.
