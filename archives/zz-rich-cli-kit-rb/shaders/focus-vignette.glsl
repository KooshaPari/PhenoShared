// focus-vignette.glsl — dim the terminal edges when the window loses focus.
//
// Uniforms used: iResolution, iChannel0, iFocus, iTimeFocus.
// `iFocus` is 1.0 while focused, 0.0 when the user has switched away.
// `iTimeFocus` is seconds since the last focus transition (resets on change).
//
// Metal-only: multi-shader OpenGL is broken in Ghostty (issue #4729).

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 col = texture(iChannel0, uv);

    // Fade into/out of the vignette over ~400 ms.
    float fade = clamp(iTimeFocus / 0.4, 0.0, 1.0);
    float target = (iFocus > 0.5) ? 0.0 : 1.0;
    float amount = mix(1.0 - target, target, fade);

    // Radial mask, smooth edge.
    vec2 centered = uv - 0.5;
    float dist = length(centered) * 1.4;
    float vignette = smoothstep(0.35, 0.95, dist);

    // Dim + slight desaturation on unfocused frames.
    vec3 gray = vec3(dot(col.rgb, vec3(0.299, 0.587, 0.114)));
    vec3 dimmed = mix(col.rgb * 0.55, gray * 0.45, 0.4);
    col.rgb = mix(col.rgb, dimmed, vignette * amount);

    fragColor = col;
}
