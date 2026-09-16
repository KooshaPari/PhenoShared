/** Glass recipe numeric values — mirror css/glass.css --glass-* vars */
export const glass = {
  neo: {
    blur: 16,
    saturate: 1.1,
    fillOpacityLight: 0.72,
    fillOpacityDark: 0.72,
    borderOpacityLight: 0.45,
    borderOpacityDark: 0.08,
    specularOpacityLight: 0.70,
    specularOpacityDark: 0.12,
    borderRadius: 16,
  },
  liquid: {
    blur: 20,
    saturate: 1.4,
    fillOpacityLight: 0.60,
    fillOpacityDark: 0.60,
    borderOpacityLight: 0.55,
    borderOpacityDark: 0.10,
    specularOpacityLight: 0.70,
    specularOpacityDark: 0.12,
    borderRadius: 14,
    /** Top-edge specular gradient stops in px */
    specularGradientHeight: '8%',
  },
  mica: {
    blur: 40,
    saturate: 1.8,
    fillOpacityLight: 0.82,
    fillOpacityDark: 0.85,
    borderOpacityLight: undefined,
    borderOpacityDark: undefined,
    borderRadius: 8,
    accentTintOpacity: 0.06,
  },
  nav: {
    blur: 14,
    saturate: 1.2,
    fillOpacity: 0.88,
  },
  badge: {
    blur: 4,
    fillOpacityDark: 0.50,
    fillOpacityLight: 0.70,
  },
} as const

export type GlassTokens = typeof glass
