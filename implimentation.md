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

This is the original version-by-version brief the project is built against.
Section 5 below expands each of these into models, endpoints, and concurrency
mechanics.

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

This is a **multi-app** Django project, not a single monolithic app. Apps are
split along domain boundaries, and each major boundary maps to one or more
version milestones below.

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
│   ├── checkin/                # Staff scan API, CheckInLog          [V4]
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
| Migration hygiene | Ticket/Reservation fields will churn a lot during V2/V3 (locking fields, QR fields). Isolating that churn from `events` keeps migration history clean per app. |
| Concurrency isolation | The two trickiest concurrency problems in this project — cart locking (`tickets`) and duplicate-scan prevention (`checkin`) — live in separate apps so their `select_for_update()` transaction logic doesn't get tangled together. |
| Matches version roadmap | Each app cluster lines up with a version milestone (V1→`accounts`+`events`, V2/V3→`tickets`, V4→`checkin`, V5→`waitlist`), so each version's work has a clean, isolated home. |
| Admin/permission scoping | Organizer vs. Staff vs. Attendee permissions differ per domain; per-app `admin.py` files scope this naturally instead of one sprawling admin file. |

Apps are created **when their version starts**, not pre-scaffolded empty ahead
of time (`tickets`, `checkin`, `waitlist` do not exist yet as of V1).

---

## 4. Roles

| Role | Capabilities |
|---|---|
| **Organizer** | Create/manage Venues and Events they own; create TicketTypes; bulk-import VIP lists; view check-in stats. |
| **Attendee** | Browse published events; purchase tickets; receive QR code; join waitlist. |
| **Staff** | Scan/validate QR codes at check-in (introduced in V4; modeled as either a `role` value on `Profile` or a boolean flag — finalized when V4 starts). |

Roles live on a `Profile` model (`OneToOneField` to `auth.User`), not a custom
user model — keeps auth machinery entirely stock Django.

---

## 5. Version-Wise Technical Plan

### V1 — Event & Venue Setup

**Spec:** Roles (Organizer, Attendee). Build Venues and Events. Implement
constraints so a venue's maximum capacity cannot be exceeded by the event's
ticket allocation.

**Models**
| Model | Key fields |
|---|---|
| `Profile` | `user` (O2O → `auth.User`), `role` (`organizer` / `attendee`) |
| `Venue` | `name`, `address`, `max_capacity` (PositiveInteger), `owner` (FK → `User`, organizer who registered it) |
| `Event` | `venue` (FK), `organizer` (FK → `User`), `name`, `description`, `date`, `status` (`draft` / `published` / `cancelled`) |

**Core constraint — capacity enforcement**
An event's total ticket allocation (sum of `TicketType.quantity_total` once
V2 introduces ticket types) can never exceed `Venue.max_capacity`. Enforced at
two layers so it can't be bypassed via forms, shell, or admin:
1. `clean()` validation at the model level (surfaces as a form/admin error).
2. A DB-level backstop — either a signal that recomputes and rejects on
   `TicketType.save()`, or a `CheckConstraint`-style guard — run inside
   `transaction.atomic()` so concurrent additions can't race past the limit.

**Access rules**
- Organizers can CRUD only their own Venues and Events.
- Attendees can view only `published` events (read-only).
- Anonymous users can browse published events but must sign up/log in to
  proceed toward purchase (purchase flow itself starts in V2).

---

### V2 — Dynamic Ticket Tiers + Cart Locking

**Spec:** Create TicketTypes (e.g., VIP, General Admission, Early Bird) with
different pricing and limited quantities. Implement cart locking to hold a
ticket for 10 minutes during checkout.

**Models**
| Model | Key fields |
|---|---|
| `TicketType` | `event` (FK), `name`, `price` (Decimal), `quantity_total`, `quantity_sold` |
| `Reservation` | `ticket_type` (FK), `user` (FK), `quantity`, `expires_at`, `status` (`active` / `expired` / `converted`) |

**Cart-locking / concurrency mechanics**
- "Add to cart" opens `transaction.atomic()`, takes `select_for_update()` on
  the `TicketType` row, checks
  `quantity_total - quantity_sold - SUM(active reservations) >= requested`,
  then creates a `Reservation` with `expires_at = now() + 10 minutes`.
- Availability queries always exclude reservations where `expires_at < now()`,
  so expired holds never appear reserved even before formal cleanup runs.
- A periodic management command (`expire_reservations`, run every ~1 minute
  via cron) flips stale `active` reservations to `expired` and releases their
  inventory for accurate reporting and for the waitlist logic in V5.
- Checkout (`Reservation` → paid `Ticket`, introduced in V3) locks the same
  row inside one atomic block, preventing double-conversion from a
  double-click or duplicate request.

---

### V3 — QR Code Generation

**Spec:** Upon successful purchase, dynamically generate a unique QR code
(string/hash) for the ticket and store it in the database.

**Models**
| Model | Key fields |
|---|---|
| `Ticket` | `reservation` (FK), `event` (FK), `ticket_type` (FK), `unique_code` (unique, high-entropy string), `qr_image` (ImageField), `status` (`valid` / `checked_in` / `refunded`) |

**Logic**
- On successful checkout, generate `unique_code = secrets.token_urlsafe(24)`
  — high-entropy, not sequential or guessable.
- Render the code as a QR PNG via the `qrcode` library, store it under
  `MEDIA_ROOT/qr/` (reusable later — e.g. re-emailing the ticket).
- The raw token is both the QR payload and the DB lookup key, which is simple
  and sufficiently secure given its entropy.

---

### V4 — Bulk Validation API

**Spec:** Create an endpoint for event staff to scan QR codes. The system
must check the database, mark the ticket as "Checked In," and reject
duplicates.

**Endpoint:** `POST /checkin/scan/` — plain Django view (no DRF), staff-only,
returns `JsonResponse`, accepts a single code or a batch (`{"codes": [...]}`).

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
- Each code in a batch is processed in its **own** atomic block, so one
  failure doesn't roll back the whole batch — the response returns
  per-code results.
- Every scan attempt (success, duplicate, or invalid) is logged to a
  `CheckInLog` model for audit and fraud detection.

---

### V5 — Bulk Import & Waitlist

**Spec:** Organizers can bulk-upload a VIP guest list via CSV to bypass
purchasing. Implement an automated waitlist that promotes the next user if a
ticket is refunded.

**Bulk CSV import**
- Organizer uploads a `name,email` CSV against a chosen `Event` +
  `TicketType`.
- Parsed via `csv.DictReader`; rows become `Ticket` records directly
  (`status='valid'`, QR generated per row) — bypassing `Reservation` and
  payment entirely.
- Wrapped in `transaction.atomic()`: if the row count exceeds remaining
  `TicketType` capacity, the **entire batch** is rejected — no partial
  imports.

**Waitlist**
| Model | Key fields |
|---|---|
| `WaitlistEntry` | `event` (FK), `ticket_type` (FK), `user` (FK), `joined_at`, `status` (`waiting` / `promoted` / `expired`) |

- Triggered when a `Ticket.status` transitions to `refunded`, handled inside
  the **same** atomic transaction as the refund (not a separate async
  signal, to avoid a race with someone else buying the freed slot).
- Locks the `TicketType` row and the oldest `WaitlistEntry`
  (`select_for_update(skip_locked=True)` for non-blocking fairness across
  concurrent refunds), creates a fresh `Reservation` for the promoted user
  with a new 10-minute window, marks the entry `promoted`, and triggers a
  notification (stub email/log for this project's scope).

---

## 6. Cross-Cutting Engineering Rules

- All inventory/monetary mutations go through `transaction.atomic()` +
  `select_for_update()` — never a bare `.save()` on a counter field.
- SQLite locks the **entire database file** on write, not just a row —
  atomic blocks are kept as short as possible, and no external I/O (email,
  QR image generation, HTTP calls) ever happens inside a lock.
- No DRF anywhere — JSON endpoints are hand-written views returning
  `JsonResponse`, protected by session auth (+ rate limiting where staff
  scanning devices are involved).
- Jinja2 is wired as a proper second `TEMPLATES` backend
  (`config/jinja2.py`), not a third-party wrapper; Django's own template
  engine is kept **only** for `django.contrib.admin`, which requires it.
- Every capacity/inventory rule is enforced at **both** the application layer
  (`clean()`, form validation) and a DB-level backstop, so it can't be
  bypassed via the admin site, shell, or a bug in a view.

---

## 7. Data Model Overview (End State, All Versions)

```
User (Django built-in)
 └── Profile            [V1]  role: organizer | attendee | (staff)
 └── Venue (owner)      [V1]  name, address, max_capacity
      └── Event         [V1]  name, date, status
           └── TicketType     [V2]  name, price, quantity_total, quantity_sold
                ├── Reservation  [V2]  user, quantity, expires_at, status
                │     └── Ticket      [V3]  unique_code, qr_image, status
                └── WaitlistEntry     [V5]  user, joined_at, status
Ticket → CheckInLog       [V4]  scanned_by, result, timestamp
```

---

## 8. Current Status

| Version | Status |
|---|---|
| V1 | Not started |
| V2 | Not started |
| V3 | Not started |
| V4 | Not started |
| V5 | Not started |

---

## 9. Step-by-Step Execution Plan for V1

| Step | Description |
|---|---|
| 1. Project Scaffolding | Django project init, dual Jinja2/Django template engine config, SQLite setup, `accounts`/`events` app skeletons, `requirements.txt`, `.gitignore` |
| 2. Accounts App (Roles) | `Profile` model, signal to auto-create on user signup, admin registration |
| 3. Auth Flows | Signup (role choice), login, logout — Jinja2 templates |
| 4. Venue Model + CRUD | Organizer-only create/edit/list/detail |
| 5. Event Model + Capacity Constraint | `clean()` validation + DB-level backstop |
| 6. Event CRUD + Public Views | Organizer CRUD + attendee-facing public listing/detail |
| 7. Constraint Verification | Prove capacity rule holds under form, ORM, and admin paths |
| 8. Base Templates & Nav | Shared layout, role-based nav, final V1 review |

Execution proceeds **one step at a time**, with explicit confirmation before
moving to the next step. Later versions (V2–V5) will get their own equivalent
step breakdowns once V1 is complete and confirmed.
