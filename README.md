<div align="center">

# 🎟️ TickIt — Event Ticketing & QR Validation Platform

**A secure, concurrency-safe event ticketing platform with cart-based holds and per-ticket QR code generation.**

Built with **Django 6.1**, **Jinja2**, **SQLite**, and a write-lock-first concurrency model — no overselling, no double-checkout, ever.

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Tests](https://img.shields.io/badge/tests-49%20passing-brightgreen)](#testing)
[![License](https://img.shields.io/badge/license-MIT-blue)](#license)

</div>

---

## 💡 The Project Idea

Most DIY ticket sellers rely on spreadsheets, and on big days the race to grab tickets turns into a free-for-all: the cart shows a seat, the buyer pays, and somehow three people bought the same spot. **TickIt** fixes that by treating ticket inventory like a real-world reservation system.

The platform lets **organizers** publish events with tiered pricing, and lets **attendees** hold tickets in a cart before buying. Every hold is time-limited and concurrency-safe, so availability is always accurate — even when hundreds of buyers hammer the same event at once. On purchase, each ticket is minted with a **unique cryptographic code** and a **QR code image**, ready to be scanned at the door (validation arriving in the next milestone).

### 🎯 Core principles

- **No overselling, ever** — availability is computed from `sold + active holds`, not just `sold`.
- **Write-lock-first concurrency** — SQLite has no row locks, so we take the database write lock *before* reading availability to serialize competing buyers (see [Architecture](#architecture)).
- **One ticket = one admission** — a cart of quantity N produces N individually-coded tickets, each with its own QR.
- **Enforced capacity everywhere** — venue capacity ≥ event allocation ≥ tier allocations, validated at the model level in both directions.

---

## ✨ Features

### 👤 Accounts (`apps.accounts`)
- Signup / login / logout with Django's hardened auth.
- Role-based profiles: **Organizer** or **Attendee**.
- `organizer_required` decorator guards all organizer-only views.

### 📅 Events & Venues (`apps.events`)
- Organizers manage venues (with capacity) and events (draft / published / cancelled).
- Capacity chain enforced: an event can't exceed its venue, and a venue can't be shrunk below an existing event's allocation.
- Public browse shows only **published** events.

### 🛒 Tickets, Cart & Holds (`apps.tickets`)
- **Ticket tiers** — organizers define multiple price tiers per event with per-tier quantities.
- **Cart with 10-minute holds** — reserving tickets locks them for 10 minutes; an `expire_reservations` management command releases expired holds.
- **Concurrency-safe reservations** — threaded stress tests prove only one of four simultaneous buyers gets the last ticket.
- **Capacity guardrails** — a tier can't be trimmed below `sold + active holds`, and tier totals can't exceed event capacity.

### 🧾 Checkout & QR Codes (v3)
- **Atomic checkout** — converts every active cart hold into real `Ticket` records inside a single transaction; a duplicate click or an expired hold is rejected, not double-charged.
- **Unique ticket codes** — `secrets.token_urlsafe(24)` with a collision loop.
- **Per-ticket QR PNGs** — generated with `qrcode`, stored under `media/qr/`, viewable on each ticket's detail page.
- **My Tickets** — attendee dashboard listing every purchased ticket with status and QR.

---

## 🧱 Architecture

```
ticketing_platform/
├── manage.py
├── requirements.txt
├── config/                  # project config
│   ├── settings.py          # SQLite, dual template engines, media, test DB
│   ├── urls.py              # includes apps + dev media serving
│   └── jinja2.py            # Jinja2 environment with url()/static globals
├── apps/
│   ├── accounts/            # Profile (roles), signup/login/logout, decorators
│   ├── events/              # Venue, Event (capacity chain, statuses)
│   └── tickets/             # TicketType, Reservation, Ticket + services
└── templates/jinja2/        # Jinja2 templates
```

### The concurrency trick

SQLite's `select_for_update()` is a no-op, so on SQLite the file-level write lock is only taken at **commit time** — meaning two concurrent reservations could both read stale availability and oversell. TickIt works around this:

```python
with transaction.atomic():
    # 1. No-op UPDATE takes the SQLite RESERVED write lock immediately,
    #    serializing concurrent writes on the same tier.
    TicketType.objects.filter(pk=ticket_type_id).update(
        quantity_sold=F("quantity_sold")
    )
    # 2. Only now is it safe to read availability and reserve.
    ticket_type = TicketType.objects.select_for_update().get(pk=ticket_type_id)
    ...
```

The same pattern is used in `checkout_cart` — lock first, then convert holds → tickets.

### Data model

| Model | Notes |
|---|---|
| `Profile` | OneToOne to `auth.User`; `role` ∈ organizer / attendee |
| `Venue` | `max_capacity`, owned by an organizer |
| `Event` | `allocated_capacity` ≤ venue capacity; status draft/published/cancelled |
| `TicketType` | per-event pricing tier; `quantity_total` / `quantity_sold` |
| `Reservation` | cart hold; `quantity`, `expires_at` (10 min), status active/expired/converted |
| `Ticket` | `unique_code` (unique), `qr_image`, status active/used/refunded/cancelled, `purchased_at` |

---

## 🚀 Getting Started

### Prerequisites
- Python **3.13** (Django 6.1 requires a modern Python)

### 1. Clone & set up

```bash
git clone https://github.com/shlok-angale/Tick-It.git
cd Tick-It/ticketing_platform

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Prepare the database

```bash
python manage.py migrate
python manage.py createsuperuser   # e.g. admin / admin12345
```

### 3. Run it

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** — sign up, choose the **Organizer** role, create a venue + published event + ticket tiers, then log in as an attendee to hold tickets and check out.

### 4. Expire stale holds

```bash
python manage.py expire_reservations
```

---

## 🧪 Testing

```bash
cd ticketing_platform
# Windows: delete any stale test DB first (file-lock quirk)
Remove-Item test_db.sqlite3 -ErrorAction SilentlyContinue
python manage.py test
```

**49 tests, all passing** — covering the capacity chain, tier guardrails, concurrency stress (4 threads racing for the last ticket), checkout conversion, duplicate-checkout protection, expired-hold rejection, QR generation, and view flows. The test suite uses a real file-based SQLite DB so threaded tests genuinely exercise locking.

## 🛠️ Tech Stack

- **Django 6.1** — ORM, auth, admin, migrations
- **Jinja2** — template engine for all app templates
- **qrcode + Pillow** — QR code PNG generation
- **SQLite** — lightweight single-file database (file-based test DB enables real concurrency tests)

---

## 📄 License

MIT
