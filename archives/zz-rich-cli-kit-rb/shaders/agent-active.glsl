// agent-active.glsl — persistent dim outer ring indicating an active agent.
//
// Toggle by symlinking or copying into Ghostty's shader dir and adding
//   custom-shader = shaders/agent-active.glsl
// to ghostty's config. User removes the line (or re-reloads) when done.
//
// No agent communication needed — ambient, time-driven only.

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 col = texture(iChannel0, uv);

    // Outer-ring mask.
    vec2 centered = uv - 0.5;
    float dist = length(centered * vec2(iResolution.x / iResolution.y, 1.0));
    float ring = smoothstep(0.55, 0.80, dist);

    // Slow breathing: 5s period, gentle amplitude.
    float breathe = 0.5 + 0.5 * sin(iTime * (6.2831853 / 5.0));
    float strength = ring * (0.10 + 0.12 * breathe);

    // Warm amber — signals "active / alive".
    vec3 tint = vec3(0.95, 0.65, 0.20);
    col.rgb = mix(col.rgb, col.rgb + tint, strength * 0.35);

    fragColor = col;
}
