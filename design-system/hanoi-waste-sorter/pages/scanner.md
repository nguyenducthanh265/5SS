# Page Override: Mangrove Flow Concept (`index.tsx`)

> Overrides `MASTER.md` with the user's atmospheric Vietnamese eco-editorial concept ("Điều Hòa Dòng Chảy — Rừng Ngập Mặn").

## 1. Visual Concept & Color Tokens
- **Atmosphere:** Soft sky-periwinkle to jade-teal flowing gradients, translucent botanical wave ribbons, and a luminous solar-halo scanner ring.
- **Light Palette (High-contrast daylight readability >= 4.5:1):**
  - Canvas Gradient: `#EAF0FF` -> `#DCF5EE` -> `#E6ECFF`
  - Frosted Card Surface: `rgba(255, 255, 255, 0.88)` with `#C7D7FE` soft border
  - Deep Indigo Ink (Primary Text): `#14224A`
  - Slate Indigo (Secondary Text): `#3B4D7A`
  - Mangrove Emerald (Primary CTA): `#0F766E` -> `#15803D` (On Primary: `#FFFFFF`)
  - Water Teal Accent: `#0284C7` / `#0D9488`
  - Solar Halo Highlight: `#FEF3C7` / `#A7F3D0` / `#BFDBFE`
- **Dark Palette (Twilight mangrove depth >= 4.5:1):**
  - Canvas Gradient: `#0A1128` -> `#102542` -> `#0B2B36`
  - Frosted Card Surface: `rgba(17, 29, 58, 0.88)` with `#2A4073` border
  - Primary Text: `#F1F5FF`
  - Secondary Text: `#CBD5F5`
- **Sorting Group Tokens (QĐ 87/2025/QĐ-UBND):**
  - `group_1_recyclable`: Jade-Emerald (`#15803D` / `#DCFCE7`)
  - `group_2_food`: Warm Solar Amber (`#B45309` / `#FEF3C7`)
  - `group_3_other`: Deep River Slate (`#334155` / `#F1F5F9`)
  - `group_3_hazardous`: Coral-Crimson Alert (`#B91C1C` / `#FEE2E2`)
  - `group_3_bulky`: Twilight Indigo (`#5B21B6` / `#EDE9FE`)

## 2. Layout & Craft Rules
- **Backdrop:** Layered SVG flowing currents + concentric solar halo behind the top header and scanner hero, never competing with text contrast (`pointerEvents="none"`).
- **Vector Icons Only:** `Ionicons` (`@expo/vector-icons`), zero structural emojis.
- **Touch & Accessibility:** Minimum `48dp` Android / `44pt` iOS touch targets, `gap >= 8`, full `accessibilityLabel` and `accessibilityRole`.
