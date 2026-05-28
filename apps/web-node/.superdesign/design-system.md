# Docstream Web — Design System

## Brand
- **Name**: Docstream
- **Tagline**: "Convert any PDF to publication-quality LaTeX"
- **Personality**: Professional, precise, modern — like a senior
  academic tool but with a clean SaaS feel
- **Feel**: Linear.app meets Vercel — clean, fast, dark,
  professional but not corporate

---

## Colors

| Token            | Hex       | Usage                        |
|------------------|-----------|------------------------------|
| `primary`        | `#1E40AF` | Deep blue, CTAs, active      |
| `accent`         | `#3B82F6` | Bright blue, highlights      |
| `bg-base`        | `#0F172A` | Page background (dark navy)  |
| `bg-surface`     | `#1E293B` | Cards, panels                |
| `border`         | `#334155` | Dividers, input borders      |
| `text-primary`   | `#F8FAFC` | Headings, body text          |
| `text-muted`     | `#94A3B8` | Captions, placeholders       |
| `success`        | `#22C55E` | Upload success, done states  |
| `error`          | `#EF4444` | Errors, failures             |
| `primary-glow`   | `rgba(59,130,246,0.15)` | Subtle glow shadows |

---

## Typography

- **Headings**: Inter — 48px / 32px / 24px / 18px
- **Body**: Inter — 16px, line-height 1.6
- **Code / Filenames**: JetBrains Mono — 13px

| Role    | Font           | Size  | Weight |
|---------|----------------|-------|--------|
| Display | Inter          | 48px  | 700    |
| H1      | Inter          | 32px  | 700    |
| H2      | Inter          | 24px  | 600    |
| H3      | Inter          | 18px  | 600    |
| Body    | Inter          | 16px  | 400    |
| Mono    | JetBrains Mono | 13px  | 400    |

---

## Spacing

Base unit: **4px**

| Token | Value | Usage                      |
|-------|-------|----------------------------|
| `1`   | 4px   | Internal padding (tight)   |
| `2`   | 8px   | Icon gaps, small gaps      |
| `3`   | 12px  | Input padding              |
| `4`   | 16px  | Component padding          |
| `6`   | 24px  | Section gaps               |
| `8`   | 32px  | Card padding               |
| `12`  | 48px  | Section separators         |
| `16`  | 64px  | Page sections              |
| `24`  | 96px  | Hero / large sections      |

---

## Border Radius

| Element    | Radius |
|------------|--------|
| Cards      | 12px   |
| Buttons    | 8px    |
| Inputs     | 6px    |
| Badges     | 4px    |
| Modals     | 16px   |

---

## Shadows & Glow

No harsh drop shadows. Use subtle glow effects only.

```css
/* Default card glow */
box-shadow: 0 0 0 1px rgba(255,255,255,0.05),
            0 0 20px rgba(59,130,246,0.08);

/* Primary button glow (hover) */
box-shadow: 0 0 20px rgba(59,130,246,0.25);

/* Error state glow */
box-shadow: 0 0 16px rgba(239,68,68,0.15);

/* Elevated modal */
box-shadow: 0 25px 50px rgba(0,0,0,0.5),
            0 0 0 1px rgba(255,255,255,0.05);
```

---

## Animation

All animations respect `prefers-reduced-motion`.

| Property   | Value          |
|------------|----------------|
| Duration   | 200–300ms      |
| Easing     | `ease-in-out`  |
| Library    | Framer Motion  |

### Standard Variants
```ts
// Fade in from below (page entry)
{ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.25 } }

// Scale in (modals, dropdowns)
{ initial: { opacity: 0, scale: 0.97 }, animate: { opacity: 1, scale: 1 }, transition: { duration: 0.2 } }

// Stagger children (lists, feature grids)
{ staggerChildren: 0.06 }
```

---

## Style

- **Dark mode first** — `#0F172A` background, never white
- **Glass morphism** cards with `backdrop-blur` on overlapping layers
- **Subtle gradients** on CTAs (`#1E40AF → #3B82F6`)
- **Smooth animations** — 200–300ms ease-in-out, Framer Motion
- **Border radius** — 12px cards, 8px buttons, 6px inputs
- **No harsh shadows** — use subtle glow: `0 0 20px rgba(59,130,246,0.15)`

---

## Components

### Buttons
| Variant     | Background    | Text      | Border          |
|-------------|---------------|-----------|-----------------|
| Primary     | `#1E40AF`     | `#F8FAFC` | none            |
| Secondary   | `#1E293B`     | `#F8FAFC` | 1px `#334155`   |
| Ghost       | transparent   | `#94A3B8` | none            |
| Destructive | `#EF4444`     | `#F8FAFC` | none            |

All buttons: 8px radius, 200ms hover transition, loading spinner during async actions.

### Cards
- Background: `#1E293B`
- Border: `1px solid rgba(255,255,255,0.06)`
- Radius: 12px
- Hover: border lightens to `rgba(255,255,255,0.12)`, subtle glow

### Inputs
- Background: `#0F172A`
- Border: `1px solid #334155`
- Radius: 6px
- Focus ring: `2px solid #3B82F6` with `box-shadow: 0 0 0 3px rgba(59,130,246,0.2)`
- Placeholder color: `#475569`

### Upload Drop Zone
- Border: `2px dashed #334155`
- Radius: 12px
- Hover: border `#3B82F6`, background `rgba(59,130,246,0.04)`
- Active drag: background `rgba(59,130,246,0.08)`, glow

### Progress Bar
- Track: `#1E293B`
- Fill: gradient `#1E40AF → #3B82F6`
- Height: 6px, radius: 3px

### Badges / Status Pills
| State      | Background               | Text      |
|------------|--------------------------|-----------|
| Processing | `rgba(245,158,11,0.15)`  | `#F59E0B` |
| Success    | `rgba(34,197,94,0.15)`   | `#22C55E` |
| Error      | `rgba(239,68,68,0.15)`   | `#EF4444` |
| Pending    | `rgba(148,163,184,0.10)` | `#94A3B8` |

---

## Key Pages

### 1. Landing (`/`)
- Hero section + upload CTA + features + "how it works"
- Full-height hero with grid/dot background texture
- Headline 48px, white, bold — tagline below in muted
- Subtle animated gradient blob in background (low opacity)
- Primary CTA button (large, 48px height)
- Feature cards in 3-column grid below the fold

### 2. Convert (`/convert`)
- Drag & drop PDF upload + template picker + progress tracker
- Stepper at top: Upload → Template → Processing → Done
- File upload zone dominates the upper half
- Template selector: horizontal scroll on mobile, grid on desktop
- Processing state: animated progress bar + live status text

### 3. Result (`/result`)
- Download `.tex` + `.pdf` + share link
- Download cards side by side, filenames in JetBrains Mono
- File size and conversion metadata shown
- "Convert another" secondary action below

---

## Dos and Don'ts

✅ **Do**
- Use glass morphism (`backdrop-blur`) for overlapping layers
- Use `#0F172A` for all page backgrounds — never white or gray
- Keep animations subtle — they should assist, not distract
- Always pair interactive elements with a focus ring for accessibility

❌ **Don't**
- Use white backgrounds anywhere
- Use colored text on colored backgrounds without contrast check
- Use `opacity: 0.5` as a substitute for proper muted text colors
- Use system default browser focus outlines — always override
