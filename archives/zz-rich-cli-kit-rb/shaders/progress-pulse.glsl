// progress-pulse.glsl — subtle bloom pulse along the bottom row.
//
// Ambient effect the user toggles on while they know an agent is working.
// No agent communication required; purely time-based.
//
// Metal-only; keep costs low.

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 col = texture(iChannel0, uv);

    // Bottom 6 % of the screen gets a moving highlight.
    float band = smoothstep(0.06, 0.0, uv.y);

    // Moving center across the band, period ~2.4 s.
    float t = fract(iTime / 2.4);
    float center = t;
    float glow = exp(-28.0 * pow(uv.x - center, 2.0));

    // Cool cyan tint, very gentle.
    vec3 tint = vec3(0.20, 0.60, 0.75);
    col.rgb += band * glow * tint * 0.35;

    fragColor = col;
}
