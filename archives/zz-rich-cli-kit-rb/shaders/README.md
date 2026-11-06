# rck-shaders

Opt-in fragment shaders for [Ghostty](https://ghostty.org/). These are GLSL,
ShaderToy-style post-process shaders. Multi-shader stacking works on macOS
(Metal) only; the OpenGL backend has an upstream bug
(ghostty-org/ghostty#4729).

## Install

```bash
rck shader install focus-vignette
rck shader install progress-pulse
rck shader install agent-active
```

Each command copies the shader into `~/.config/ghostty/shaders/<name>.glsl`
(or `$XDG_CONFIG_HOME/ghostty/shaders/`) and prints the line to add to your
Ghostty config:

```
# ~/.config/ghostty/config
custom-shader = shaders/focus-vignette.glsl
custom-shader-animation = true
```

`custom-shader-animation = true` keeps `iTime` advancing when the terminal is
idle — required for `progress-pulse` and `agent-active`.

## Shaders

| Name | What it does | Uniforms |
|------|--------------|---------:|
| `focus-vignette` | Dim + desaturate edges when the window loses focus. | `iFocus`, `iTimeFocus` |
| `progress-pulse` | Subtle cyan pulse travelling along the bottom row. | `iTime` |
| `agent-active`   | Persistent warm outer-ring breathing effect. | `iTime` |

## Why not success/failure tints?

Agent-triggered transient tints (green on OSC 133;D exit=0, red on non-zero)
would need a new Ghostty uniform (`iAgentStatus` or similar) to expose the
terminal-side event to the shader. That's an upstream feature request, not
something `rck` can ship today. See
[`docs/ghostty_capabilities.md §3`](../docs/ghostty_capabilities.md) for the
feasibility analysis.
