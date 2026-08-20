# Event Ticketing & QR Validation Platform

A Django-based ticketing platform handling event/venue management, tiered
ticket sales with concurrency-safe inventory locking, dynamic QR code
generation, staff check-in validation, and bulk import/waitlist automation.

The core engineering challenge of this project is **concurrency correctness**:
preventing overselling of tickets under simultaneous checkouts, and preventing
duplicate check-ins under simultaneous scans — both on a database (SQLite)
that locks the whole file on write, not just a row.

---

## 1. Original Feature Specification

> **8. Event Ticketing & QR Validation Platform**
> Requires handling concurrency (to prevent overselling tickets) and
> generating dynamic data.
>
> **V1 (Event & Venue Setup):** Roles (Organizer, Attendee). Build Venues and
> Events. Implement constraints so a venue's maximum capacity cannot be
> exceeded by the event's ticket allocation.
>
> **V2 (Dynamic Ticket Tiers):** Create TicketTypes (e.g., VIP, General
> Admission, Early Bird) with different pricing and limited quantities.
> Implement cart locking to hold a ticket for 10 minutes during checkout.
>
> **V3 (QR Code Generation):** Upon successful purchase, dynamically generate
> a unique QR code (string/hash) for the ticket and store it in the database.
>
> **V4 (Bulk Validation API):** Create an endpoint for event staff to scan QR
> codes. The system must check the database, mark the ticket as "Checked In,"
> and reject duplicates.
>
> **V5 (Bulk Import & Waitlists):** Organizers can bulk-upload a VIP guest
> list via CSV to bypass purchasing. Implement an automated waitlist that
> promotes the next user if a ticket is refunded.

**Hard constraints for this build:**
- Django standard views only — **no Django REST Framework (DRF)**.
- **Jinja2** templating (via Django's built-in Jinja2 backend).
- **SQLite** database.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | Django 5.1.x | Standard Django views — **no DRF**. JSON API endpoints are hand-rolled `JsonResponse` views. |
| Templating | Jinja2 | Via Django's built-in `django.template.backends.jinja2.Jinja2` engine (not the `django-jinja` third-party package). |
| Database | SQLite | `db.sqlite3`. Locking strategy designed around SQLite's whole-file write lock (short-lived `atomic()` blocks, no I/O inside transactions). |
| QR generation | `qrcode` + `Pillow` | Generates PNG from a high-entropy token; no external QR service. |
| CSV import | Python stdlib `csv` | No pandas dependency. |
| Auth | Django's built-in `auth.User` + a `Profile` model for roles | No custom user model — `Profile` is a `OneToOneField` to `User` carrying `role`. |
| Background expiry | Django management command (`expire_reservations`), run via cron | No Celery/Redis — kept lightweight per project scope. |

---

## 3. Project Structure — Multi-App Django Project

Multi-app, split along domain boundaries — each boundary maps to one or more
version milestones.

```
ticketing_platform/
├── manage.py
├── requirements.txt
├── .gitignore
├── db.sqlite3
├── config/                    # Project-level config (not an "app")
│   ├── settings.py
│   ├── urls.py                # Root URLconf, includes each app's urls.py
│   ├── jinja2.py              # Jinja2 Environment (adds `url`, `static` globals)
│   ├── wsgi.py / asgi.py
├── apps/
│   ├── accounts/               # Users, roles, profiles              [V1]
│   ├── events/                 # Venue, Event                        [V1]
│   ├── tickets/                # TicketType, Reservation, Ticket, QR [V2, V3]
│   ├── checkin/                # Secret-link scan view, CheckInLog   [V4]
│   └── waitlist/               # WaitlistEntry, bulk CSV import      [V5]
├── templates/
│   └── jinja2/
│       ├── base/                # shared layout, nav
│       ├── accounts/
│       ├── events/
│       ├── tickets/             (added in V2)
│       ├── checkin/              (added in V4)
│       └── waitlist/             (added in V5)
├── static/
└── media/
    └── qr/                       # generated QR PNGs (V3)
```

### Why multi-app (not single-app)

| Reason | Detail |
|---|---|
| Domain separation | `accounts`, `events`, `tickets`, `checkin`, `waitlist` are each independently reasoned-about domains with their own models and workflows. |
| Migration hygiene | Ticket/Reservation fields churn heavily during V2/V3 (locking fields, QR fields). Isolating that churn from `events` keeps migration history clean per app. |
| Concurrency isolation | Cart locking (`tickets`) and duplicate-scan prevention (`checkin`) are the two trickiest concurrency problems here — separate apps keep their `select_for_update()` logic from tangling together. |
| Matches version roadmap | V1→`accounts`+`events`, V2/V3→`tickets`, V4→`checkin`, V5→`waitlist`. |
| Admin/permission scoping | Organizer vs. Attendee permissions differ per domain; per-app `admin.py` scopes this naturally. |

Apps are created **when their version starts** — `tickets`, `checkin`,
`waitlist` do not exist yet as of V1.

---

## 4. Roles & Access Model

This is the finalized access model after working through the actual usage
flow (not just the abstract spec).

| Role | Account type | Capabilities |
|---|---|---|
| **Admin** | Django **superuser** (`is_superuser`) | Full visibility into everything via `/admin`. Not a domain concept — no role-based logic gates them, they bypass it entirely as Django's built-in superuser. |
| **Organizer** | Real `User` + `Profile(role='organizer')` | Creates and manages their own Venues, Events, TicketTypes; bulk-uploads VIP CSVs; edits their event's banner/accent-color "canvas"; generates/regenerates the check-in secret link. Sees **only their own** events/venues — never another organizer's. |
| **Attendee** | Real `User` + `Profile(role='attendee')` | Browses a public dashboard of `published` events; can also reach a specific event directly via its unique link/QR; buys tickets; receives a QR pass after purchase. |
| **Check-in scanner ("staff")** | **No account at all** | Accesses a per-event secret scan link (`/checkin/<scan_token>/`), no login. Enters an optional free-text "scanner name" once per session (stored client-side) purely for attribution in the check-in log — not authentication. |

### Important naming note
Django's `User.is_staff` (controls `/admin` access) is **unrelated** to the
spec's "staff" who scan QR codes at the door. To avoid confusion in code and
docs, the scanning role is referred to as **"check-in scanner"** or just
**"scanner"** internally — never `is_staff`.

### Attendee access — two entry points, not one
- **Dashboard** — a public listing of all `published` events (title, date,
  banner thumbnail), similar in shape to a standard events calendar (e.g.
  WeMakeDevs' public event listing). This is the primary discovery path.
- **Direct link/QR** — every event also has a clean, unique public URL that
  can be shared directly (poster, social post, DM) and works independently
  of the dashboard. Both paths lead to the same event detail/purchase page.

### Check-in scanner — why a secret link, not a PIN or shared session
- **No login required** — works for however many volunteers/devices need to
  scan simultaneously (important for events with real foot traffic at the
  door, not just a single organizer's phone).
- **Instantly revocable** — if the link leaks, the organizer regenerates
  `Event.scan_token` and the old link stops working immediately.
- **Attribution without accounts** — the optional scanner-name prompt gives
  per-scan attribution in `CheckInLog` without requiring anyone to register.

---

## 5. Venues — Ownership & Management

- **Organizers manage venues themselves**, self-service — same pattern as
  Events. No admin involvement required to create or use a venue.
- `Venue.owner` is a `ForeignKey` to the organizer who created it.
- **Every venue query is scoped to the requesting organizer:**
  `Venue.objects.filter(owner=request.user)` — organizers never see or edit
  another organizer's venues. Each organizer effectively has a private venue
  library.
- **Reusable across events** — a venue is created once and can be attached to
  multiple events over time (e.g. a recurring meetup space), rather than
  being re-entered per event.
- **CRUD flow:**
  1. "My Venues" list — name, address, `max_capacity`, count of events using it.
  2. Create — simple form; `owner` is set server-side from `request.user`,
     never trusted from client input.
  3. Edit/Delete — same ownership check on every view (`venue.owner !=
     request.user` → 404, not 403, to avoid revealing existence).
  4. **Event's venue dropdown is queryset-scoped** to the organizer's own
     venues — this matters beyond UI, since an unscoped queryset would let a
     malicious POST reference another organizer's venue ID directly.
  5. **Delete protection:** `on_delete=PROTECT` on the `Event.venue` FK —
     deleting a venue that still has events attached is blocked outright,
     rather than cascading and silently destroying those events.

---

## 6. Version-Wise Technical Plan

### V1 — Event & Venue Setup

**Spec:** Roles (Organizer, Attendee). Build Venues and Events. Implement
constraints so a venue's maximum capacity cannot be exceeded by the event's
ticket allocation.

**Models**
| Model | Key fields |
|---|---|
| `Profile` | `user` (O2O → `auth.User`), `role` (`organizer` / `attendee`) |
| `Venue` | `name`, `address`, `max_capacity` (PositiveInteger), `owner` (FK → `User`, `on_delete=PROTECT` from `Event`) |
| `Event` | `venue` (FK, `on_delete=PROTECT`), `organizer` (FK → `User`), `name`, `description`, `date`, `status` (`draft`/`published`/`cancelled`), `public_slug` (unique, for direct-link access), `banner_image`, `accent_color` (canvas fields) |

**Core constraint — capacity enforcement**
An event's total ticket allocation (sum of `TicketType.quantity_total` once
V2 lands) can never exceed `Venue.max_capacity`. Enforced at two layers:
1. `clean()` validation (form/admin-level UX).
2. DB-level backstop (signal or constraint check inside
   `transaction.atomic()`) so concurrent additions can't race past the limit,
   and the rule can't be bypassed via shell/admin.

**Access rules**
- Organizers CRUD only their own Venues and Events (see Section 5).
- Attendees see only `published` events, via dashboard or direct link.
- Anonymous users can browse published events but must sign up/log in to
  purchase (purchase flow starts V2).

---

### V2 — Dynamic Ticket Tiers + Cart Locking

**Spec:** Create TicketTypes (e.g., VIP, General Admission, Early Bird) with
different pricing and limited quantities. Implement cart locking to hold a
ticket for 10 minutes during checkout.

**Models**
| Model | Key fields |
|---|---|
| `TicketType` | `event` (FK), `name`, `price` (Decimal), `quantity_total`, `quantity_sold` |
| `Reservation` | `ticket_type` (FK), `user` (FK), `quantity`, `expires_at`, `status` (`active`/`expired`/`converted`) |

**Cart-locking / concurrency mechanics**
- "Add to cart" opens `transaction.atomic()`, `select_for_update()` on the
  `TicketType` row, checks
  `quantity_total - quantity_sold - SUM(active reservations) >= requested`,
  creates a `Reservation` with `expires_at = now() + 10 minutes`.
- Availability queries always exclude expired reservations at query time.
- Periodic `expire_reservations` management command (cron, ~1 min) formally
  flips stale reservations and releases inventory for accurate reporting and
  the V5 waitlist trigger.
- Checkout locks the same row in one atomic block — prevents
  double-conversion from double-click/duplicate requests.

---

### V3 — QR Code Generation

**Spec:** Upon successful purchase, dynamically generate a unique QR code
(string/hash) for the ticket and store it in the database.

**Models**
| Model | Key fields |
|---|---|
| `Ticket` | `reservation` (FK), `event` (FK), `ticket_type` (FK), `unique_code` (unique, high-entropy), `qr_image` (ImageField), `status` (`valid`/`checked_in`/`refunded`) |

**Logic**
- `unique_code = secrets.token_urlsafe(24)` — high-entropy, not guessable.
- Rendered as a QR PNG via `qrcode`, stored under `MEDIA_ROOT/qr/`.
- Raw token doubles as both the QR payload and DB lookup key.

---

### V4 — Bulk Validation API (Secret-Link Scanning)

**Spec:** Create an endpoint for event staff to scan QR codes. The system
must check the database, mark the ticket as "Checked In," and reject
duplicates.

**Access:** `Event.scan_token` (unique, regenerable) — no user account.
Scan page lives at `/checkin/<scan_token>/`; the token itself is the auth.
Organizer can regenerate the token at any time to instantly revoke the old
link. First visit prompts for an optional free-text scanner name, stored
client-side (session) for attribution only.

**Endpoint:** `POST /checkin/<scan_token>/scan/` — plain Django view, no DRF,
`JsonResponse`, accepts a single code or a batch (`{"codes": [...]}`).

**Per-code logic (inside `transaction.atomic()`):**
```
ticket = Ticket.objects.select_for_update().get(unique_code=code)
if ticket.status == 'checked_in':
    → reject as duplicate (409)
if ticket.status != 'valid':
    → reject as invalid/refunded (400)
ticket.status = 'checked_in'
ticket.checked_in_at = now()
ticket.save()
```
- Each code in a batch processed in its own atomic block — one failure
  doesn't roll back the rest; response returns per-code results.
- Every scan attempt (success/duplicate/invalid) logged to `CheckInLog`
  (`ticket`, `result`, `scanner_name`, `timestamp`) for audit.

---

### V5 — Bulk Import & Waitlist

**Spec:** Organizers can bulk-upload a VIP guest list via CSV to bypass
purchasing. Implement an automated waitlist that promotes the next user if a
ticket is refunded.

**Bulk CSV import**
- Organizer uploads `name,email` CSV against an `Event` + `TicketType`.
- Parsed via `csv.DictReader`; rows become `Ticket` records directly
  (`status='valid'`, QR generated per row) — bypasses `Reservation`/payment.
- Wrapped in `transaction.atomic()`: row count exceeding remaining capacity
  rejects the **entire batch** — no partial imports.

**Waitlist**
| Model | Key fields |
|---|---|
| `WaitlistEntry` | `event` (FK), `ticket_type` (FK), `user` (FK), `joined_at`, `status` (`waiting`/`promoted`/`expired`) |

- Triggered on `Ticket.status → refunded`, inside the **same** atomic
  transaction as the refund (avoids racing a concurrent purchase for the
  freed slot).
- Locks `TicketType` row + oldest `WaitlistEntry`
  (`select_for_update(skip_locked=True)` for fairness across concurrent
  refunds), creates a fresh `Reservation` with a new 10-minute window for the
  promoted user, marks entry `promoted`, stub-notifies them.

---

## 7. Cross-Cutting Engineering Rules

- All inventory/monetary mutations go through `transaction.atomic()` +
  `select_for_update()` — never a bare `.save()` on a counter field.
- SQLite locks the **entire database file** on write — atomic blocks stay as
  short as possible; no external I/O (email, QR generation, HTTP) inside a
  lock.
- No DRF anywhere — hand-written views returning `JsonResponse`.
- Jinja2 wired as a proper second `TEMPLATES` backend (`config/jinja2.py`);
  Django's own template engine kept **only** for `django.contrib.admin`.
- Every capacity/inventory rule enforced at **both** the application layer
  (`clean()`) and a DB-level backstop.
- All owner-scoped resources (`Venue`, `Event`, etc.) are filtered by
  `owner=request.user` / `organizer=request.user` at the **queryset** level,
  not just hidden in the UI — dropdowns and forms are scoped the same way to
  prevent cross-organizer access via crafted requests.

---

## 8. Data Model Overview (End State, All Versions)

```
User (Django built-in)
 └── Profile                [V1]  role: organizer | attendee
 └── Venue (owner)          [V1]  name, address, max_capacity
      └── Event             [V1]  name, date, status, public_slug,
          │                       banner_image, accent_color, scan_token
           └── TicketType        [V2]  name, price, quantity_total, quantity_sold
                ├── Reservation    [V2]  user, quantity, expires_at, status
                │     └── Ticket        [V3]  unique_code, qr_image, status
                └── WaitlistEntry       [V5]  user, joined_at, status
Ticket → CheckInLog          [V4]  scanner_name, result, timestamp
(Admin = Django superuser — no dedicated model, full /admin visibility)
```

---

## 9. Current Status

| Version | Status |
|---|---|
| V1 | Not started |
| V2 | Not started |
| V3 | Not started |
| V4 | Not started |
| V5 | Not started |

---

## 10. Step-by-Step Execution Plan for V1

| Step | Description |
|---|---|
| 1. Project Scaffolding | Django project init, dual Jinja2/Django template engine config, SQLite setup, `accounts`/`events` app skeletons, `requirements.txt`, `.gitignore` |
| 2. Accounts App (Roles) | `Profile` model, signal to auto-create on user signup, admin registration |
| 3. Auth Flows | Signup (role choice), login, logout — Jinja2 templates |
| 4. Venue Model + CRUD | Organizer-only, owner-scoped create/edit/list/detail |
| 5. Event Model + Capacity Constraint | `clean()` validation + DB-level backstop; `public_slug`, canvas fields (`banner_image`, `accent_color`) |
| 6. Event CRUD + Public Views | Organizer CRUD + attendee-facing dashboard (published events list) and direct-link detail page |
| 7. Constraint Verification | Prove capacity rule holds under form, ORM, and admin paths |
| 8. Base Templates & Nav | Shared layout, role-based nav, final V1 review |

Execution proceeds **one step at a time**, with explicit confirmation before
moving to the next step. Later versions (V2–V5) get their own equivalent step
breakdowns once V1 is complete and confirmed.
