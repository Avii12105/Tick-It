# Event Ticketing & QR Validation Platform — Design Language

## 1. Purpose

This document defines the **visual design language** for the Event Ticketing & QR Validation Platform.

The attached Gimi Michi reference is used **only as visual inspiration**. The goal is **not** to reproduce its webpage structure, sections, content, or product-card layout.

The platform should feel like its own event-ticketing product while borrowing the reference's:

- street-editorial energy
- warm paper-like backgrounds
- condensed display typography
- black graphic outlines
- orange and red accents
- selective neon color
- print/poster textures
- imperfect collage details
- high-contrast visual hierarchy
- energetic but controlled graphic composition

The result should be a **modern event platform with a distinctive editorial identity**, not a recreation of the reference site.

---

# 2. Design Principles

### 2.1 Editorial, not corporate

Avoid the conventional SaaS appearance of:

- large rounded cards
- excessive white space
- soft grey borders
- generic blue/purple product palettes
- excessive drop shadows
- glassmorphism

Use:

- strong typography
- visible borders
- poster-like composition
- graphic accents
- hard-edged shadows
- asymmetric details
- compact information blocks

### 2.2 Bold but functional

Visual elements should create personality without interfering with:

- event discovery
- ticket selection
- checkout
- QR display
- QR scanning
- organizer management

Critical information always has higher visual priority than decoration.

### 2.3 Contemporary with print-inspired details

The interface should sit between:

```text
DIGITAL EVENT PLATFORM
        +
EDITORIAL POSTER
        +
KOREAN STREET-STYLE GRAPHICS
```

---

# 3. Overall Visual Personality

Use these descriptors as the north-star for implementation:

```text
BOLD
EDITORIAL
YOUTHFUL
GRAPHIC
PRINT-INSPIRED
ENERGETIC
HIGH-CONTRAST
SLIGHTLY IMPERFECT
CULTURAL
MODERN
```

Avoid making the UI:

```text
CORPORATE
MINIMAL-SAAS
GLASSY
SOFT
GENERIC
OVERLY-CUTE
OVERLY-DECORATED
```

---

# 4. Color System

The reference uses a warm base with saturated accent colors. Adapt that principle to the ticketing platform.

## 4.1 Core colors

```css
:root {
  --paper: #FFFAEF;
  --paper-dark: #F3EAD8;

  --ink: #151313;
  --ink-soft: #2A2522;

  --orange: #F7AA28;
  --orange-dark: #D98916;

  --red: #B52D28;
  --red-dark: #7E211E;

  --maroon: #631F24;

  --violet: #32246E;
  --purple: #51318D;

  --cyan: #16CFD5;
  --pink: #FF4B9B;

  --white: #FFFFFF;

  --success: #2F7C42;
  --warning: #C98512;
  --danger: #B52D28;

  --muted: #776F64;
}
```

## 4.2 Color roles

### Paper

Primary application background.

```css
background: var(--paper);
```

### Ink

Primary text, borders, icons, dividers and graphic outlines.

### Orange

Primary visual accent.

Use for:

- main CTAs
- selected states
- highlighted statistics
- important event labels
- ticket availability
- featured information

### Red / Maroon

Use for:

- warnings
- urgency
- sold-out states
- cancelled events
- destructive actions
- strong secondary accents

### Violet / Purple

Use selectively for:

- event-specific themes
- dark promotional sections
- hero backgrounds

### Cyan / Pink

Use sparingly as high-energy neon accents.

These should appear mostly in:

- hero graphics
- selected decorative elements
- active scanner feedback
- special event themes

They should **not** become the application's default functional colors.

---

# 5. Color Proportions

A typical page should visually follow approximately:

```text
65%  warm paper / cream
18%  black / dark ink
9%   orange / gold
5%   red / maroon
3%   neon accents
```

The exact ratio may change by page.

The key rule is:

> Neon is an accent, not the foundation.

---

# 6. Typography

Typography is one of the strongest elements borrowed from the reference.

## 6.1 Display font

Use a condensed display font:

```css
font-family: "Bebas Neue", "Arial Narrow", Impact, sans-serif;
```

Alternative:

```css
font-family: "Anton", "Arial Narrow", Impact, sans-serif;
```

Use for:

- page titles
- event titles
- major statistics
- ticket-tier names
- large calls to action
- important status messages

Characteristics:

- uppercase
- condensed
- heavy
- tight line-height
- compact letter spacing

Example:

```text
DISCOVER
WHAT'S NEXT.
```

Instead of:

```text
Discover what's happening next
```

when the text is functioning as a major visual heading.

## 6.2 Body font

Use:

```css
font-family: Inter, "Helvetica Neue", Arial, sans-serif;
```

Use for:

- descriptions
- metadata
- dates
- addresses
- forms
- navigation
- buttons when clarity matters

## 6.3 Accent script

A handwritten display font may be used in very small doses:

```css
font-family: "Pacifico", cursive;
```

Suitable for:

- a one-word event accent
- handwritten annotations
- decorative campaign text

Do not use script typography for essential information.

---

# 7. Typography Scale

Desktop:

| Role | Size | Style |
|---|---:|---|
| Display hero | 64–96px | condensed, uppercase |
| Page heading | 42–64px | condensed, uppercase |
| Section heading | 30–46px | condensed, uppercase |
| Event title | 22–34px | condensed |
| Ticket heading | 20–28px | condensed |
| Body | 14–17px | sans-serif |
| Metadata | 11–13px | sans-serif, uppercase |
| Micro-label | 8–10px | bold uppercase |

Mobile:

| Role | Size |
|---|---:|
| Hero | 42–58px |
| Page heading | 32–44px |
| Section heading | 26–36px |
| Event title | 21–28px |
| Body | 14–16px |

Do not reduce critical text below readable sizes simply to reproduce the reference aesthetic.

---

# 8. Typography Hierarchy

A screen should typically have only three typography levels:

```text
LEVEL 1
VERY LARGE CONDENSED DISPLAY

LEVEL 2
MEDIUM CONDENSED SECTION TITLE

LEVEL 3
CLEAN SANS-SERIF INFORMATION
```

This creates the contrast seen in the reference without copying its layout.

---

# 9. Letter Spacing and Case

Display typography:

```css
text-transform: uppercase;
letter-spacing: -0.015em;
```

Metadata:

```css
text-transform: uppercase;
letter-spacing: 0.04em;
```

Body copy:

```css
text-transform: none;
letter-spacing: normal;
```

Avoid excessive tracking on large headings.

---

# 10. Background Style

The default background is warm, not pure white.

```css
body {
  background: var(--paper);
  color: var(--ink);
}
```

## Optional paper texture

A very subtle grain can be added:

```css
.paper {
  background-color: var(--paper);

  background-image:
    radial-gradient(
      rgba(20, 19, 17, 0.045) 0.7px,
      transparent 0.7px
    );

  background-size: 7px 7px;
}
```

Texture should be nearly invisible at normal reading distance.

---

# 11. Graphic Texture Vocabulary

Use a small set of recurring graphic textures.

## 11.1 Grid

Thin geometric grids suggest posters, packaging and event graphics.

```css
.grid-texture {
  background-image:
    linear-gradient(rgba(20,19,17,.10) 1px, transparent 1px),
    linear-gradient(90deg, rgba(20,19,17,.10) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

## 11.2 Halftone

```css
.halftone {
  background-image:
    radial-gradient(
      rgba(20,19,17,.13) 0.8px,
      transparent 0.8px
    );
  background-size: 7px 7px;
}
```

## 11.3 Noise

Use extremely light grain over large promotional surfaces.

## 11.4 Hand-drawn marks

Use:

- arrows
- circles
- stars
- underlines
- short strokes
- rough rectangular highlights

These should appear as accents, not everywhere.

---

# 12. Borders

Borders are important to the visual identity.

Default:

```css
border: 1px solid var(--ink);
```

Strong:

```css
border: 2px solid var(--ink);
```

Use visible borders on:

- event cards
- ticket cards
- form controls
- important status panels
- modal windows
- QR passes

Avoid invisible or ultra-light grey borders.

---

# 13. Corner Radius

The reference relies more on rectangular framing than rounded UI.

Use:

```css
--radius-sm: 2px;
--radius-md: 4px;
--radius-pill: 999px;
```

Main components:

```text
RECTANGULAR
```

not:

```text
LARGE ROUNDED SAAS CARD
```

Pills are reserved for small status labels.

---

# 14. Shadow Language

Use hard offset shadows rather than large blurred shadows.

Primary:

```css
box-shadow: 4px 4px 0 var(--ink);
```

Accent:

```css
box-shadow: 4px 4px 0 var(--orange);
```

Small:

```css
box-shadow: 2px 3px 0 rgba(20, 19, 17, .20);
```

The shadow should look like a physical object offset from a printed page.

---

# 15. Asymmetry

One of the important stylistic traits to carry over is **controlled imperfection**.

Examples:

- a label shifted slightly outside a card
- an image rotated by 1–3 degrees
- a sticker overlapping a border
- a heading intentionally broken into two lines
- an accent line extending beyond a component

Use asymmetry selectively.

The layout itself should still remain predictable and accessible.

---

# 16. Decorative Stickers

Create a small reusable sticker system.

Examples:

```text
NEW
LIVE
LIMITED
VIP
EARLY BIRD
SOLD OUT
JUST ADDED
2 DAYS LEFT
```

Visual treatment:

- compact
- uppercase
- bold
- rectangular
- black outline
- orange/red fill

Example:

```css
.sticker {
  display: inline-block;
  padding: 4px 8px;
  border: 1px solid var(--ink);
  background: var(--orange);
  color: var(--ink);
  font-family: var(--font-display);
  text-transform: uppercase;
}
```

Small rotations of ±2 degrees are acceptable for decorative stickers.

---

# 17. Lines and Dividers

Use graphic dividers rather than generic whitespace alone.

Examples:

```text
────────────────────────
```

or:

```text
──────── ✦ ────────
```

or a segmented neon line in promotional areas.

CSS:

```css
.editorial-divider {
  height: 1px;
  background: var(--ink);
  position: relative;
}
```

Major sections may use a thicker 2px rule.

---

# 18. Neon Treatment

The reference has a strong neon graphic language. Use that language only in selected places.

A reusable neon treatment can be:

```css
.neon-surface {
  background:
    radial-gradient(circle at 75% 20%, var(--cyan), transparent 25%),
    radial-gradient(circle at 25% 70%, var(--pink), transparent 25%),
    linear-gradient(135deg, #14122D, var(--violet), #24164B);
}
```

Add graphic rails:

```css
.neon-line {
  border-top: 3px solid var(--pink);
  box-shadow: 0 0 8px rgba(255, 75, 155, .5);
}
```

Use for:

- featured-event hero
- special event campaign
- major event announcement
- scanner success moment
- promotional states

Do not use neon on every screen.

---

# 19. Image Style

Event images should feel like:

```text
POSTER
+
EDITORIAL PHOTOGRAPHY
+
SOCIAL CONTENT
```

Preferred characteristics:

- strong crop
- visible image framing
- high contrast
- occasional color treatment
- occasional text overlay
- occasional stickers

Avoid:

- generic corporate stock-photo style
- identical rounded 16:9 cards
- excessive blur
- large soft shadows

---

# 20. Event Visual Identity

Each event should have its own visual identity while remaining inside the platform's design system.

The `Event.banner_image` and `Event.accent_color` fields defined in the project plan should be used as the primary event-level customization inputs. fileciteturn0file0L182-L195

The organizer should be able to change:

```text
EVENT IMAGE
+
EVENT ACCENT COLOR
```

without changing the platform's typography, spacing, or core paper/ink foundation.

Therefore:

```text
PLATFORM IDENTITY
        +
EVENT-SPECIFIC ACCENT
```

rather than:

```text
EVERY EVENT HAS A COMPLETELY DIFFERENT UI
```

---

# 21. Event Accent Color Rules

An event accent color may control:

- event highlight
- CTA accent
- graphic strokes
- badges
- selected navigation state
- poster details
- ticket edge accents

The following should remain stable:

- body typography
- default page background
- standard form styling
- accessibility treatment
- functional success/error semantics

For example:

```text
Event A → Orange accent
Event B → Red accent
Event C → Purple accent
Event D → Cyan accent
```

All four should still look like the same platform.

---

# 22. Cards

Cards should use a **poster/editorial** appearance.

Recommended:

```css
.card {
  background: var(--paper);
  border: 1px solid var(--ink);
  box-shadow: 3px 3px 0 rgba(20,19,17,.16);
}
```

Cards should not automatically have:

- 16px+ corner radius
- giant shadow
- glass transparency
- large internal padding

---

# 23. Event Card Language

Event cards should communicate:

```text
IMAGE
EVENT NAME
DATE
VENUE
PRICE / AVAILABILITY
ACTION
```

The exact layout can remain conventional for usability.

The **styling**, not the reference webpage composition, creates the shared design language.

Example:

```text
┌───────────────────────────┐
│ EVENT IMAGE               │
│                           │
│ [LIVE]                    │
├───────────────────────────┤
│ MUSIC & CULTURE           │
│ MIDNIGHT SEOUL            │
│ 17 SEP • 7 PM             │
│ GRAND HALL                │
│                           │
│ FROM ₹499                 │
│                           │
│ [VIEW EVENT]              │
└───────────────────────────┘
```

---

# 24. Ticket Cards

Ticket tiers from V2 should borrow the reference's printed-product feeling without copying the source layout.

Use:

```text
physical ticket
+
paper stock
+
black outline
+
accent strip
```

Example:

```text
┌──────────────────────────────┐
│ VIP                      ₹1499│
│ ─────────────────────────────│
│ Premium entry                │
│ Preferred seating            │
│                              │
│ 18 REMAINING                 │
│                              │
│ [RESERVE]                    │
└──────────────────────────────┘
```

A perforation line or ticket-notch detail may be used.

---

# 25. Ticket Perforation

Use a simple CSS treatment.

```css
.ticket {
  position: relative;
  border: 2px solid var(--ink);
}

.ticket::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 54px;
  border-top: 1px dashed var(--ink);
}
```

Small circular cutouts can be added on both sides.

Keep the effect subtle.

---

# 26. Buttons

Buttons should feel like bold labels from a printed poster.

Primary:

```css
.btn-primary {
  background: var(--orange);
  color: var(--ink);
  border: 2px solid var(--ink);
  padding: 10px 18px;
  box-shadow: 3px 3px 0 var(--ink);

  font-family: var(--font-display);
  text-transform: uppercase;
}
```

Secondary:

```css
.btn-secondary {
  background: var(--paper);
  color: var(--ink);
  border: 2px solid var(--ink);
}
```

Danger:

```css
.btn-danger {
  background: var(--red);
  color: var(--white);
  border: 2px solid var(--ink);
}
```

Avoid giant pill buttons.

---

# 27. Button Interaction

Hover:

```css
transform: translate(2px, 2px);
box-shadow: 1px 1px 0 var(--ink);
```

Focus:

```css
outline: 2px solid var(--orange);
outline-offset: 2px;
```

Pressed state should visually flatten the button.

This creates a small tactile print-like effect.

---

# 28. Navigation

The navigation should be clean and restrained.

Use the reference's compact graphic language rather than reproducing its specific header structure.

Characteristics:

- warm paper background
- black text
- thin lower border
- condensed labels
- small orange active indicator
- compact spacing

Example:

```text
EVENTS     VENUES     MY TICKETS     ABOUT

                         [LOGIN]
                         [CREATE EVENT]
```

The navigation itself should remain conventional because it is a primary usability element.

---

# 29. Hero Language

The platform may use a strong promotional hero, but this should remain a **design option**, not a requirement that every page copy the reference.

Recommended hero characteristics:

- dark background
- large condensed headline
- one dominant image or graphic
- orange primary CTA
- one or two neon graphic accents
- thin horizontal rules
- small micro-labels

Example:

```text
NEXT UP

LIVE MUSIC.
NO SMALL MOVES.

17 SEP
MUMBAI

[GET TICKETS]
```

The hero should promote an event rather than mimic the source site's advertising campaign.

---

# 30. Information Density

The reference demonstrates strong visual information density.

Use compact groups such as:

```text
17 SEP • 7 PM • MUMBAI
```

rather than spreading the same metadata across a large amount of whitespace.

Recommended compact metadata style:

```css
.meta {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .04em;
}
```

---

# 31. Forms

Forms should use the same paper/ink system.

```css
input,
select,
textarea {
  background: #FFFDF7;
  border: 1px solid var(--ink);
  border-radius: 0;
  padding: 10px 12px;
}
```

Focus:

```css
outline: 2px solid var(--orange);
outline-offset: 2px;
```

Form labels:

- uppercase
- compact
- bold
- clear

Do not decorate forms excessively.

---

# 32. Dashboard Design

The organizer dashboard should **not** become a full poster collage.

Instead, apply the design language through:

- typography
- borders
- colors
- section headers
- graphic accents
- compact statistics
- hard shadows

Example:

```text
MY EVENTS.

12 EVENTS      842 TICKETS      731 CHECKED IN
```

Then use clear operational cards/tables.

The dashboard must remain efficient for management tasks.

---

# 33. Statistics

Large statistics are a good place for the condensed type.

Example:

```text
842
TICKETS SOLD
```

or:

```text
731
CHECKED IN
```

Use orange for the most important number.

Keep explanatory text in the body font.

---

# 34. Status System

Functional status must remain visually clear.

| Status | Main color |
|---|---|
| Valid | Green |
| Checked in | Green |
| Held | Orange |
| Limited | Orange |
| Waiting | Maroon |
| Sold out | Red |
| Refunded | Red |
| Cancelled | Red |
| Expired | Muted / maroon |

Always include the textual status.

Do not rely on color alone.

---

# 35. QR Ticket

The generated QR ticket should borrow the **printed-pass feeling** rather than looking like a generic QR-code page.

Use:

- cream background
- black border
- bold condensed event name
- QR code
- event metadata
- ticket type
- status
- unique ticket code
- small accent-color strip

Example:

```text
────────────────────────────
LIVE EVENT
MIDNIGHT SEOUL

AVINASH VORA
VIP

17 SEP 2026
7:00 PM
GRAND HALL

        [ QR ]

VALID
CODE: 8F93A...
────────────────────────────
```

The QR quiet zone must remain completely clear.

---

# 36. Scanner UI

The scanner needs to be functional first.

The visual inspiration should appear only through:

- black framing
- cream interface
- neon scan corners
- condensed title
- strong status typography

Example:

```text
CHECK-IN

┌──────────────────────┐
│                      │
│       QR AREA        │
│                      │
└──────────────────────┘

READY TO SCAN
```

Success:

```text
ENTRY APPROVED
```

Duplicate:

```text
ALREADY CHECKED IN
```

Invalid:

```text
INVALID TICKET
```

The result should be immediate and impossible to miss.

---

# 37. Scanner Neon Treatment

The scanner is one place where neon can have a functional role.

Idle:

```text
black / cream
```

Scanning:

```text
pink / cyan scan corners
```

Valid:

```text
green feedback
```

Duplicate:

```text
red feedback
```

Invalid:

```text
maroon / red feedback
```

The scanner should not use decorative elements that obstruct camera visibility.

---

# 38. Checkout

Checkout should be visually consistent but operationally calm.

Use:

```text
cream page
black typography
orange action
paper-like order summary
strong ticket visuals
```

The active 10-minute reservation should be visually emphasized because V2 requires the reservation to expire after 10 minutes. fileciteturn0file0L205-L225

Example:

```text
09:42 LEFT

YOUR TICKETS
VIP × 2

ORDER TOTAL
₹2998

[CHECKOUT]
```

---

# 39. Reservation Countdown

Use boxed digits:

```text
09 : 42
MIN SEC
```

Style:

```css
.countdown-digit {
  background: var(--white);
  border: 1px solid var(--ink);
}
```

At less than two minutes, shift the accent toward red.

At expiration:

```text
RESERVATION EXPIRED
```

---

# 40. Public Event Detail

The event detail page should simply use the design language across a conventional event-page structure.

Recommended:

```text
EVENT IMAGE / HERO
↓
TITLE
↓
DATE + VENUE
↓
DESCRIPTION
↓
TICKET TYPES
↓
AVAILABILITY
↓
VENUE INFORMATION
↓
BOOKING CTA
```

Do not force unnecessary collage sections into the page.

The reference influences styling, not information architecture.

---

# 41. Category Styling

Event categories may use graphic tiles with:

- strong color blocks
- simple patterns
- large condensed labels
- line-art icons
- image fragments

Examples:

```text
TECH
MUSIC
CULTURE
COMEDY
SPORTS
WORKSHOPS
```

Use irregularity in visual treatment, but preserve consistent sizing and interaction behavior.

---

# 42. Editorial Image Frames

For occasional event stories or organizer spotlights, use printed-photo styling.

```css
.photo-frame {
  background: var(--white);
  border: 1px solid var(--ink);
  padding: 7px;
  box-shadow: 4px 5px 0 rgba(20,19,17,.15);
}
```

A small rotation is allowed:

```css
transform: rotate(-2deg);
```

Use this selectively.

---

# 43. Decorative Graphic Library

Build a reusable set of simple SVG/CSS decorations:

```text
star
circle
arrow
underline
neon-line
ticket-notch
burst
grid
halftone
scribble
small cross
bracket
```

Each should be usable independently.

The platform should rely on a **small visual vocabulary** rather than dozens of unrelated decorative elements.

---

# 44. Iconography

Icons should be:

- simple
- line-based
- black or ink
- visually compact

Recommended style:

```text
1.5–2px stroke
minimal fill
rounded or geometric line endings
```

Avoid highly detailed 3D icons.

Icons are secondary to typography.

---

# 45. Empty States

Empty states may use oversized display typography and a small graphic accent.

Example:

```text
NO EVENTS
YET.

CREATE YOUR
FIRST EVENT.
```

Then:

```text
[CREATE EVENT]
```

A small star, arrow, grid or ticket outline can sit behind the heading.

---

# 46. Error States

Errors should remain visually strong.

Example:

```text
TICKET
COULD NOT
BE RESERVED.

The selected quantity is no longer available.

[TRY AGAIN]
```

Use red only where meaningful.

Do not turn entire screens red.

---

# 47. Modal Style

Modals should use a paper/poster look:

```css
.modal {
  background: var(--paper);
  border: 2px solid var(--ink);
  box-shadow: 6px 6px 0 var(--ink);
}
```

Use straightforward layout and copy.

Decoration is optional.

---

# 48. Toast Style

Use compact, graphic notifications.

Example:

```text
✓ TICKET RESERVED
10-MINUTE HOLD ACTIVE
```

```text
× RESERVATION EXPIRED
```

```text
! ONLY 3 TICKETS LEFT
```

Style:

- paper background
- black border
- hard shadow
- one accent color

---

# 49. Tables

Operational organizer tables should remain clear.

Style them with:

```text
black / ink header
cream body
orange active highlights
thin rules
compact typography
```

Do not sacrifice usability for editorial styling.

---

# 50. Spacing

Use a compact but deliberate spacing system.

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 24px;
--space-6: 32px;
--space-7: 48px;
--space-8: 64px;
--space-9: 96px;
```

Important:

The reference has visually dense sections but also uses large intentional section breaks.

Therefore:

```text
SMALL SPACING
inside information groups

LARGE SPACING
between major ideas
```

---

# 51. Layout Width

Recommended:

```css
--content-width: 1240px;
```

Desktop padding:

```css
padding-inline: clamp(20px, 4vw, 48px);
```

Do not make the application unnecessarily narrow.

Event imagery and poster typography benefit from a wide layout.

---

# 52. Responsive Strategy

## Desktop

Emphasize:

- large display typography
- event imagery
- multi-column cards
- editorial composition
- selective overlap

## Tablet

Reduce:

- overlap
- decorative density
- type scale

Keep the same visual identity.

## Mobile

Prioritize:

```text
CONTENT
+
TICKET ACTION
+
READABILITY
```

The mobile experience should feel like a compact poster/feed rather than trying to squeeze the desktop composition into a small screen.

---

# 53. Mobile Rules

On mobile:

- keep display typography large
- use full-width cards
- stack ticket tiers vertically
- make primary actions easy to reach
- reduce decorative layers
- preserve black borders
- preserve paper background
- preserve orange accents
- keep neon only for important promotional surfaces

Avoid horizontal overflow caused by decorative graphics.

---

# 54. Motion

Use subtle, tactile motion.

Good:

- 150–250ms button movement
- slight image zoom
- sticker rotation correction
- small neon glow
- scanner status transition

Avoid:

- slow cinematic page transitions
- excessive parallax
- constant movement
- distracting animations around ticket information

Motion should support the graphic identity rather than become the identity.

---

# 55. Component Design Philosophy

Components should have a clear hierarchy.

For example:

```text
EventCard
├── EventImage
├── StatusBadge
├── EventTitle
├── EventMeta
├── EventPrice
└── PrimaryButton
```

The **component structure remains conventional**.

The reference-inspired style is expressed through:

- typography
- color
- borders
- texture
- composition
- graphic accents

This keeps the codebase maintainable.

---

# 56. Suggested Design Tokens

```css
:root {
  /* Colors */
  --color-bg: #FFFAEF;
  --color-bg-alt: #F3EAD8;
  --color-ink: #151313;
  --color-orange: #F7AA28;
  --color-red: #B52D28;
  --color-maroon: #631F24;
  --color-violet: #32246E;
  --color-purple: #51318D;
  --color-cyan: #16CFD5;
  --color-pink: #FF4B9B;
  --color-success: #2F7C42;
  --color-muted: #776F64;

  /* Typography */
  --font-display: "Bebas Neue", "Arial Narrow", Impact, sans-serif;
  --font-body: Inter, "Helvetica Neue", Arial, sans-serif;
  --font-script: "Pacifico", cursive;

  /* Radius */
  --radius-card: 3px;
  --radius-button: 2px;
  --radius-pill: 999px;

  /* Borders */
  --border-thin: 1px solid var(--color-ink);
  --border-thick: 2px solid var(--color-ink);

  /* Shadows */
  --shadow-print: 4px 4px 0 var(--color-ink);
  --shadow-soft-print: 3px 4px 0 rgba(20,19,17,.16);

  /* Width */
  --content-width: 1240px;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;
  --space-8: 64px;
  --space-9: 96px;
}
```

---

# 57. Suggested CSS Base

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-ink);
  font-family: var(--font-body);
  line-height: 1.45;
}

h1,
h2,
h3,
h4,
h5,
h6 {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 800;
  line-height: .92;
  text-transform: uppercase;
}

button,
input,
select,
textarea {
  font: inherit;
}

img {
  display: block;
  max-width: 100%;
}

button {
  cursor: pointer;
}
```

---

# 58. Accessibility Rules

The design language must not reduce accessibility.

Required:

- sufficient text contrast
- visible keyboard focus
- semantic headings
- readable body text
- accessible form labels
- descriptive image alt text
- explicit status text
- keyboard-accessible controls
- QR fallback code in text
- scanner feedback communicated through text and color

The aesthetic should never be used as a reason to reduce usability.

---

# 59. V1 Application

For V1, apply this visual language to:

- signup
- login
- navigation
- organizer dashboard
- venue list
- venue forms
- event list
- event create/edit
- public event dashboard
- public event detail
- base responsive shell

The existing project plan defines organizer/attendee roles, organizer-owned venues/events, published-event discovery, direct event links, and event banner/accent-color fields. The design system should support those workflows without changing their information architecture. fileciteturn0file0L110-L134

---

# 60. V2 Application

When ticket functionality is added, apply the same design language to:

- ticket tier cards
- quantity controls
- availability
- cart/reservation status
- 10-minute countdown
- checkout
- order summary

V2 introduces `TicketType` and 10-minute reservations, so the visual language should communicate scarcity and temporary holds clearly. fileciteturn0file0L205-L225

---

# 61. V3 Application

For V3:

- digital ticket
- QR code
- ticket status
- unique ticket code

The generated QR ticket should look like a **digital event pass**, not a generic database record. fileciteturn0file0L231-L243

---

# 62. V4 Application

For V4:

- mobile-first scanner
- scan state
- valid result
- duplicate result
- invalid/refunded result
- scanner attribution

The visual system should become more functional here: use graphic framing and strong typography, but minimize decorative noise because the scanner must operate quickly at the venue entrance. fileciteturn0file0L248-L276

---

# 63. V5 Application

For V5:

- CSV upload
- import status
- waitlist
- promotion
- capacity failure

Use the same paper/ink/print language for these administrative screens without turning them into promotional pages. fileciteturn0file0L281-L305

---

# 64. What Is Being Borrowed From the Reference

### Borrow

- warm cream background
- bold condensed display type
- black graphic outlines
- orange/gold as an energetic anchor
- red/maroon supporting color
- selective neon pink/cyan/purple
- grid and halftone textures
- poster-like graphics
- hard offset shadows
- stickers and micro-labels
- controlled asymmetry
- editorial photography treatment
- print-inspired UI details

### Do not reproduce

- the exact webpage layout
- the exact hero structure
- the exact section order
- food/ramen imagery
- product-sale concepts
- source-brand identity
- source logos
- exact decorative artwork
- exact copy
- exact card arrangements
- exact navigation
- exact content hierarchy

The platform should be recognizably its own product.

---

# 65. Final Visual Target

The final product should look approximately like:

```text
MODERN EVENT PLATFORM
          +
KOREAN-INSPIRED EDITORIAL GRAPHICS
          +
PRINT / POSTER AESTHETIC
          +
HIGH-CONTRAST TICKET UX
```

A user should immediately notice:

```text
cream paper
black condensed type
orange energy
small red accents
occasional neon
graphic borders
poster-like event imagery
```

but should **not** feel that the entire interface is a copy of the reference webpage.

---

# 66. Final Implementation Rule

When a design decision is unclear, follow this priority:

```text
1. FUNCTIONALITY
2. READABILITY
3. ACCESSIBILITY
4. PLATFORM CONSISTENCY
5. REFERENCE-INSPIRED VISUAL STYLE
6. DECORATION
```

The reference is the **visual vocabulary**, not the product architecture.

The event-ticketing platform's information architecture, workflows, roles, concurrency behavior, QR validation, and V1–V5 implementation remain governed by the existing project plan. fileciteturn0file0L14-L39
