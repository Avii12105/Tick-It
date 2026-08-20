# UI Design — "Box-Office Ticket Stock"

This document specifies the visual design system for the Event Ticketing &
QR Validation Platform: the theme rationale, design tokens, and how they
apply across every screen in the app. It complements `DESIGN.md` (technical
architecture) — this file is purely about what the app looks and feels like.

---

## 1. Design Rationale

The subject of this product is a physical artifact: **the admission ticket**
— tear-stub, perforation, ink stamp, dot-matrix ticket number. Rather than
defaulting to a generic SaaS dashboard look, the UI is grounded in that
artifact directly. Attendee-facing screens read like tickets; organizer
screens read like a box-office back office — same world, two different
vantage points.

**What this deliberately avoids:**
- Warm cream background + serif display + terracotta accent (the most
  common AI-generated default look).
- Near-black background with a single neon/bright accent and nothing else
  distinguishing it.
- Broadsheet/newspaper hairline-rule, zero-radius layouts.

Instead: a cool "thermal ticket paper" surface floating on a graphite "night
box-office" background, with die-cut perforation circles and dashed tear
lines as the recurring signature motif.

---

## 2. Design Tokens

### 2.1 Color

| Token | Hex | Role |
|---|---|---|
| `ink` | `#1B1E24` | Page background — box-office-at-night graphite |
| `paper` | `#E8ECEE` | Ticket-stock surface for cards, panels |
| `graphite` | `#2B2A26` | Primary text on `paper` |
| `stamp` | `#D6472B` | Primary accent — rubber ink-stamp red. CTAs, "sold out," destructive actions |
| `valid` | `#3F7D58` | Success/validated state — "checked in," "available" tags |
| `gold` | `#C99A3E` | Tier accent — VIP/premium badges, foil-stamp feel |
| `muted-ink` | `#5F5E5A` | Secondary text on `paper` (labels, eyebrows) |
| `paper-line` | `#2B2A26` at low opacity | Perforation/divider lines on paper surfaces |

**Usage rule:** `ink` is reserved for page backgrounds only — content never
sits directly on `ink` without a `paper` surface underneath it. `stamp` is
used sparingly (one primary action per view, plus status flags) — it is not
a general-purpose accent to sprinkle around.

### 2.2 Typography

| Role | Typeface | Used for |
|---|---|---|
| Display | Archivo Narrow / Big Shoulders Display (bold, compressed) | Event names, page headlines only — used with restraint |
| Mono | IBM Plex Mono / JetBrains Mono | Ticket codes, prices, dates, tier counts, QR labels, ledger tables — anything that reads as "data" |
| Body | Inter / Public Sans | Descriptions, form labels, everything conversational |

**Type scale:**
- Display: 28–34px, weight 700, tight line-height (1.1)
- Body: 15–16px, weight 400, line-height 1.6
- Mono (data): 12–14px, weight 500–700 depending on emphasis
- Eyebrow/label: 11px, mono, letter-spacing 0.08em, `muted-ink`

### 2.3 Layout Primitives

- **Card radius:** 10px (paper cards) — enough to feel like stiff cardstock, not a soft rounded-rect
- **Perforation:** 1px dashed line (`paper-line`, 60% ink / 40% transparent, 8px repeat) with 12px die-cut circles (filled `ink`, matching the page background) at each end
- **Border weight:** hairline (0.5–1px) everywhere except the 2px accent border reserved for a single highlighted/featured item per view (e.g. "recommended tier")
- **Spacing rhythm:** 8px base unit; card padding 20px, section gaps 32–48px

---

## 3. The Signature Element — Ticket Stub Card

Every event, everywhere it's listed, renders as a stub card: a wide "info"
panel plus a narrow "stub" panel, divided by the dashed perforation with
die-cut circle notches at top and bottom of the divider.

```
┌─────────────────────────────┬┄┄┄┐
│ GENERAL ADMISSION            ⊙  │
│ DEVCON MEETUP #14            :  │
│ Grand Hall · Mumbai          :  │
│                        [VIP] ⊙  │  AUG
│                                  │  24
│                              $45│
│                          12 LEFT│
└─────────────────────────────┴┄┄┄┘
```

- **Info side:** eyebrow (tier/category), event name (display type), venue
  line (body type), tier badge if applicable (gold pill).
- **Stub side:** mono date (month abbreviation + day, stacked), price, and
  an availability tag (`valid` green "N left" or `stamp` red "sold out").
- **Hover interaction (desktop only):** the two halves separate by 3–4px, as
  if the ticket is being pulled apart — the one deliberate motion signature
  in the whole app. No other hover effects compete with it.
- **Reduced motion:** hover separation is disabled entirely when
  `prefers-reduced-motion` is set; the card still indicates interactivity via
  a border-color shift instead.

This card is used, with size variants, in: the attendee dashboard grid, the
event detail page header, and the organizer's "my events" list (a flatter,
denser variant — see Section 5).

---

## 4. Attendee-Facing Screens

### 4.1 Dashboard (`/events/`)
- Public listing of `published` events only.
- Grid of stub cards, `repeat(auto-fit, minmax(320px, 1fr))`, on the `ink`
  background — the cards are the only light elements on the page, which is
  the intended visual tension (tickets scattered on a dark counter).
- Filter/search bar sits above the grid, styled as a simple mono-labeled
  input, not a heavy toolbar.
- Empty state (no published events): a single stub card rendered in outline
  only ("no shows on the board yet"), not a generic illustration.

### 4.2 Event Detail / Purchase Page (`/events/<id>/` or direct link)
- Full-width "boarding pass" treatment: the stub card scales up as the page
  header (banner image, if the organizer set one, fills the info side's
  background at low opacity behind the text — canvas customization applies
  here).
- Below the header: ticket tier selection, each tier as a row (not another
  stub card — tiers are a list, not individually decorated) with name,
  price (mono), availability, and a quantity stepper.
- Primary CTA ("Reserve tickets") is the one `stamp`-colored button on the
  page — reinforces the "you get one accent, spend it here" rule.
- Countdown timer for an active 10-minute hold is rendered in mono type,
  small, next to the cart — a ticking number, not a progress bar (matches
  the "ticket counter" register rather than a generic UI widget).

### 4.3 Cart / Reservation Hold
- A simple paper panel listing held items, expiry countdown per line, and a
  "release" action styled as ghost/secondary (not `stamp`-colored — that's
  reserved for forward-moving actions, not cancellation).

### 4.4 Ticket / QR Pass (post-purchase, V3)
- The full stub-card metaphor pays off here: the actual owned ticket is
  rendered as a stub card with the QR code occupying the stub side (replacing
  the date/price mono block), and a "VALID" or "CHECKED IN" stamp graphic
  (rotated slightly, `valid` green or `graphite`, semi-transparent) overlaid
  once scanned.

---

## 5. Organizer-Facing Screens

Organizer views intentionally use a **different register of the same
system** — a will-call ledger/manifest, not the decorated stub-card look.
Real box-office back-office tools are dense and utilitarian; the organizer
side should read that way.

- **Layout:** dense mono-type tables on `paper`-toned rows (alternating
  `paper` and a very slightly darker paper tone for zebra-striping), directly
  on the `ink` page background with minimal card chrome.
- **"My Venues" / "My Events" lists:** table rows, not cards — name, capacity,
  status, event count, all in mono where the value is numeric or a code.
- **Event edit form (including canvas customization):** a plain form using
  body type for labels, with a small live preview of the stub card off to
  the side so the organizer sees banner/accent-color changes reflected
  immediately — this is the one place a live "mockup within the UI" pattern
  is justified.
- **CSV bulk import (V5):** an upload dropzone styled like a manifest intake
  slot — plain, bordered, mono filename display once a file is selected, no
  decorative dropzone illustration.
- **Status colors follow the same semantic tokens** as attendee views
  (`valid` = published/available, `stamp` = draft/action-needed/cancelled,
  `gold` reserved only for tier badges, not status).

---

## 6. Check-In Scanner Screen (V4)

This is a **single-purpose, high-contrast utility screen** — designed for a
phone at a doorway, glanced at quickly, often in low light.

- Full-screen dark (`ink`) background, minimal chrome.
- Large centered camera viewport for the QR scan (or manual code entry
  fallback in mono type below it).
- Result feedback is a full-screen color flash, not a small toast:
  - **Valid scan:** `valid` green flash, ticket holder name in display type,
    tier in mono.
  - **Duplicate:** `stamp` red flash, "already checked in" plus original
    scan timestamp in mono.
  - **Invalid/refunded:** `stamp` red flash, reason stated plainly.
- Optional scanner-name prompt appears once, styled as a simple mono input,
  stored for the session — not a login form, must not resemble one.
- No perforation/stub motif here — this screen is function-first; the
  ticket metaphor belongs to the attendee's *possession* of a ticket, not to
  the door staff's tool.

---

## 7. Shared Components

| Component | Treatment |
|---|---|
| Primary button | `stamp` fill, `paper`-toned text, 10px radius, mono label for ticket-related actions ("Reserve," "Check in"), body type for general actions |
| Secondary/ghost button | Transparent, hairline `graphite` border, no fill |
| Status badge | Pill, mono type, colored per token (`valid`/`stamp`/`gold`), text uses the darkest available shade of its own family, never plain black |
| Form input | `paper` fill, hairline border, mono type only for numeric/code fields (price, capacity, quantity) — body type for names/descriptions |
| Empty state | Outline-only stub card or ledger row, single line of plain-voice copy, one action |
| Error message | Plain body copy, `stamp`-toned text, states what happened and what to do — no apology, no exclamation marks |

---

## 8. Accessibility & Responsiveness

- Contrast: `graphite` on `paper` and `paper` on `ink` both exceed WCAG AA;
  colored badges use the 800/900-equivalent shade of their family for text,
  never a lighter tint, to hold contrast on small pill backgrounds.
- Visible focus states on every interactive element (hairline ring in
  `stamp` or `valid` depending on context) — never removed for aesthetics.
- `prefers-reduced-motion` disables the stub-card separation hover and any
  page-load stagger; content still communicates state via color/border
  changes.
- Mobile: stub cards stack full-width; the two-panel (info/stub) layout
  collapses to stacked (info on top, stub details as a row beneath) below
  ~480px rather than shrinking illegibly.
- Scanner screen (Section 6) is mobile-first by definition — designed at
  360px width first, scaled up.

---

## 9. What's Designed but Not Yet Built

Per `DESIGN.md` Section 9, `Event.banner_image` and `Event.accent_color`
(the canvas fields referenced throughout Sections 4.2 and 5) are not yet
implemented in the data model — this document specifies how they'll be used
once they land, not a claim that they're live today. Similarly, the QR pass
(4.4) and scanner screen (Section 6) describe V3/V4 designs ahead of
implementation.
