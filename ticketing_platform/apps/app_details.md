# Apps Folder Detailed Analysis

Scope analyzed: all Python files under `Tick-It/ticketing_platform/apps`.

## 1) File-by-file working

### Root package

#### `apps/__init__.py`

- Purpose: Marks `apps` as a Python package.
- Runtime behavior: No executable logic.
- Importance: Allows imports like `apps.accounts`, `apps.events`, `apps.tickets`.

---

## Accounts app

#### `apps/accounts/__init__.py`

- Purpose: Package marker for accounts app.
- Runtime behavior: No executable logic.

#### `apps/accounts/admin.py`

- Registers `Profile` in Django admin.
- `ProfileAdmin` behavior:
  - `list_display`: shows user and role.
  - `list_filter`: filters by role.
  - `search_fields`: supports searching by related user username/email.
- Working impact: Makes user-role management easy for staff.

#### `apps/accounts/apps.py`

- Defines `AccountsConfig`.
- In `ready()`, imports `apps.accounts.signals`.
- Working impact: Ensures profile-creation signal is always connected when app boots.

#### `apps/accounts/decorators.py`

- Defines `organizer_required` decorator.
- Flow:
  - If user is anonymous: redirect to login and preserve `next` URL.
  - If authenticated but not organizer: show error message and redirect home.
  - If organizer: allow view execution.
- Working impact: Central role-based access control for organizer-only endpoints.

#### `apps/accounts/forms.py`

- Defines `SignupForm` extending `UserCreationForm`.
- Adds role selection field using `Profile.Role` choices.
- Requires email in form init.
- Working impact: Signup captures both auth credentials and app-level role.

#### `apps/accounts/models.py`

- Defines `Profile` model as one-to-one extension of Django user.
- Role values are controlled via `TextChoices`.
- Includes `is_organizer` convenience property.
- Working impact: Single source of truth for role checks throughout the project.

#### `apps/accounts/signals.py`

- `post_save` receiver on user model.
- Flow:
  - On user creation: create related `Profile`.
  - On user update: save existing profile.
- Working impact: Prevents missing profile rows for normal user-creation paths.

#### `apps/accounts/tests.py`

- Tests key account behaviors:
  - profile auto-creation,
  - signup role persistence,
  - login behavior,
  - authenticated-user signup redirect behavior.
- Working impact: Protects account onboarding/auth flow from regressions.

#### `apps/accounts/urls.py`

- URL endpoints:
  - signup,
  - login (class-based view),
  - logout.
- Working impact: Routing entry point for authentication workflows.

#### `apps/accounts/views.py`

- `UserLoginView`: login page/view integration.
- `signup` view flow:
  - blocks already-authenticated users,
  - validates form,
  - creates user,
  - writes selected role to profile,
  - logs in user,
  - redirects to home with success message.
- Working impact: End-to-end registration bootstrap in one place.

#### `apps/accounts/migrations/__init__.py`

- Migration package marker.

#### `apps/accounts/migrations/0001_initial.py`

- Creates `Profile` table schema with role and one-to-one user link.
- Depends on swappable auth user model migration state.

---

## Events app

#### `apps/events/__init__.py`

- Package marker for events app.

#### `apps/events/admin.py`

- Registers `Venue` and `Event`.
- Admin optimizations include `select_related` for event organizer/venue in list pages.
- Working impact: Better admin usability and fewer queries in list rendering.

#### `apps/events/apps.py`

- Defines `EventsConfig`.
- Imports `apps.events.signals` in `ready()`.
- Working impact: Save-time capacity validations are always enforced.

#### `apps/events/forms.py`

- `VenueForm`: CRUD form for venue details.
- `EventForm`:
  - uses HTML5 datetime-local widget,
  - supports expected datetime input format,
  - can scope venue queryset to organizer-owned venues when organizer is passed.
- Working impact: Prevents organizers from selecting venues they do not own.

#### `apps/events/models.py`

- Defines:
  - `Venue`,
  - `Event`,
  - `validate_venue_capacity` helper.
- Core rules:
  - Venue cannot be shrunk below already-allocated event capacity.
  - Event allocated capacity cannot exceed venue max capacity.
- Working impact: Capacity planning rules are enforced at model layer.

#### `apps/events/signals.py`

- `pre_save` validations for `Event` and `Venue`.
- Working impact: Guards capacity invariants even if `full_clean()` is skipped in calling code.

#### `apps/events/tests.py`

- Validates:
  - model/signal capacity constraints,
  - organizer access control and ownership scoping,
  - public visibility restrictions (published events only).
- Working impact: Ensures organizer/public split and capacity logic remain correct.

#### `apps/events/urls.py`

- Provides both public and organizer routes.
- Public: event listing/detail.
- Organizer: venue/event CRUD and organizer detail/list screens.
- Working impact: Clear separation between customer and organizer interfaces.

#### `apps/events/views.py`

- Public flow:
  - home/list shows published events,
  - detail allows only published events.
- Organizer flow:
  - all organizer views protected by `organizer_required`,
  - queryset filtering enforces ownership,
  - organizer event detail computes ticket capacity usage using ticket tiers.
- Working impact: Main orchestration point for event lifecycle and presentation.

#### `apps/events/migrations/__init__.py`

- Migration package marker.

#### `apps/events/migrations/0001_initial.py`

- Creates `Venue` and `Event` tables.
- Key FK behavior:
  - `Event.venue` uses `PROTECT`.
  - `Event.organizer` uses `CASCADE`.

---

## Tickets app

#### `apps/tickets/__init__.py`

- Package marker for tickets app.

#### `apps/tickets/admin.py`

- Registers `TicketType` and `Reservation`.
- Admin shows computed availability for ticket types using model method.
- Working impact: Admin can quickly inspect inventory and reservation state.

#### `apps/tickets/apps.py`

- Defines `TicketsConfig`.
- Imports `apps.tickets.signals` in `ready()`.
- Working impact: Ticket capacity checks are enforced pre-save globally.

#### `apps/tickets/forms.py`

- `TicketTypeForm`: organizer ticket-tier form.
- `AddToCartForm`:
  - validates selected tier,
  - enforces positive quantity.
- Working impact: First-level request validation before service-level stock validation.

#### `apps/tickets/models.py`

- Defines:
  - `TicketType`,
  - `Reservation`,
  - `validate_ticket_type_capacity` helper.
- Key inventory logic:
  - availability = total - sold - active_nonexpired_reservations,
  - active reservations affect inventory instantly.
- Working impact: Encodes stock, hold, and oversell protection in domain model.

#### `apps/tickets/services.py`

- Defines reservation lock duration constant and `reserve_tickets` service.
- Flow:
  - validates quantity,
  - opens atomic transaction,
  - applies lock strategy suitable for SQLite behavior,
  - reloads tier,
  - enforces event is published,
  - checks dynamic availability,
  - creates active reservation with expiry.
- Working impact: Core anti-oversell transactional boundary for cart adds.

#### `apps/tickets/signals.py`

- `pre_save` receiver enforces ticket type capacity constraints.
- Working impact: Safety net for write paths that bypass forms/services.

#### `apps/tickets/tests.py`

- Broad coverage:
  - ticket capacity invariants,
  - reservation lifecycle,
  - cart flow,
  - expiration command,
  - concurrency/oversell protection.
- Working impact: Validates high-risk ticketing logic across race conditions and edge cases.

#### `apps/tickets/urls.py`

- Routes for:
  - attendee cart actions,
  - organizer ticket type create/update/delete.
- Working impact: Single routing surface for reservation and tier management flows.

#### `apps/tickets/views.py`

- Attendee flow:
  - `cart`,
  - `add_to_cart` (form validation -> auth handling -> service call),
  - `remove_from_cart`.
- Organizer flow:
  - ticket type CRUD scoped to organizer-owned events/tiers,
  - surfaces used capacity for decision support.
- Working impact: Main HTTP layer bridging forms and service logic.

#### `apps/tickets/management/commands/expire_reservations.py`

- Management command to expire stale active reservations.
- Performs bulk update: active and past expiry -> expired.
- Working impact: Operational cleanup for hold lifecycle and clearer observability.

#### `apps/tickets/migrations/__init__.py`

- Migration package marker.

#### `apps/tickets/migrations/0001_initial.py`

- Creates `TicketType` and `Reservation` tables.
- Adds DB check constraint so sold quantity cannot exceed total quantity.
- Depends on events initial migration and auth user model.

---

## 2) Detailed model analysis

### `Profile` model (`apps/accounts/models.py`)

- Purpose:
  - Extends auth user with platform role.

- Fields:
  - `user`: `OneToOneField` -> auth user, `on_delete=CASCADE`, `related_name='profile'`.
  - `role`: `CharField(max_length=20)`, choices from `Profile.Role`, default attendee.

- Relationships:
  - Exactly one profile per user (enforced by one-to-one).

- Methods and behavior:
  - `is_organizer`: role equality helper, used by authorization checks.
  - `__str__`: returns readable username-role representation.

- Integrity implications:
  - App code commonly assumes `request.user.profile` exists; this is supported by post-save signal auto-creation.

- Performance/index notes:
  - One-to-one implies uniqueness/index on user relation.

### `Venue` model (`apps/events/models.py`)

- Purpose:
  - Represents organizer-owned venue with max capacity.

- Fields:
  - `name`: `CharField(max_length=200)`.
  - `address`: `TextField(blank=True)`.
  - `max_capacity`: `PositiveIntegerField`.
  - `owner`: `ForeignKey` -> auth user, `on_delete=CASCADE`, `related_name='venues'`.
  - `created_at`: `DateTimeField(auto_now_add=True)`.

- Relationships:
  - One owner can have many venues.
  - Venue can have many events (`Event.venue`).

- Methods and behavior:
  - `clean()` calls `validate_venue_capacity`.
  - Validation prevents lowering venue capacity below allocations already committed by its events.

- Meta:
  - Ordering by newest first (`-created_at`).

- Integrity implications:
  - Prevents impossible downsizing after event capacities are assigned.
  - Save-time signal duplicates this validation for stronger enforcement.

### `Event` model (`apps/events/models.py`)

- Purpose:
  - Represents event content, publication state, and allocated ticket capacity budget.

- Fields:
  - `venue`: `ForeignKey` -> Venue, `on_delete=PROTECT`, `related_name='events'`.
  - `organizer`: `ForeignKey` -> auth user, `on_delete=CASCADE`, `related_name='events'`.
  - `name`: `CharField(max_length=200)`.
  - `description`: `TextField(blank=True)`.
  - `date`: `DateTimeField`.
  - `allocated_capacity`: `PositiveIntegerField`.
  - `status`: `CharField(max_length=20)`, choices draft/published/cancelled, default draft.
  - `created_at`: `DateTimeField(auto_now_add=True)`.

- Relationships:
  - Event belongs to one venue and one organizer.
  - Event has many ticket types.

- Methods and behavior:
  - `clean()` enforces `allocated_capacity <= venue.max_capacity`.
  - Status enum controls public visibility and reservation eligibility.

- Meta:
  - Ordering by newest first (`-created_at`).

- Integrity implications:
  - `PROTECT` on venue keeps event references valid.
  - Capacity constraints prevent over-allocating beyond venue.

### `TicketType` model (`apps/tickets/models.py`)

- Purpose:
  - Defines sellable ticket tier inventory and pricing for an event.

- Fields:
  - `event`: `ForeignKey` -> Event, `on_delete=CASCADE`, `related_name='ticket_types'`.
  - `name`: `CharField(max_length=100)`.
  - `price`: `DecimalField(max_digits=10, decimal_places=2)`.
  - `quantity_total`: `PositiveIntegerField`.
  - `quantity_sold`: `PositiveIntegerField(default=0)`.

- Relationships:
  - One event can have multiple ticket tiers.
  - One ticket tier can have multiple reservations.

- Methods and behavior:
  - `reserved_count`: sums ACTIVE reservations whose `expires_at` is still in future.
  - `available_count`: dynamic inventory (`total - sold - active_holds`).
  - `clean()` calls `validate_ticket_type_capacity`.
  - `allocated_total(event)`: sums all tier totals for an event.

- Capacity constraints:
  - `quantity_total` cannot be less than sold.
  - `quantity_total` cannot be less than sold + active held reservations.
  - Aggregate `quantity_total` across event tiers cannot exceed `Event.allocated_capacity`.

- Meta and constraints:
  - Ordering by `price` then `name`.
  - DB check constraint: sold <= total.

- Integrity implications:
  - Multi-layer checks (DB + model clean + pre-save signal) reduce risk of invalid stock states.
  - Availability depends on reservation expiry timing, so operational expiry jobs matter.

### `Reservation` model (`apps/tickets/models.py`)

- Purpose:
  - Time-bound hold for tickets in cart flow.

- Fields:
  - `ticket_type`: `ForeignKey` -> TicketType, `on_delete=CASCADE`, `related_name='reservations'`.
  - `user`: `ForeignKey` -> auth user, `on_delete=CASCADE`, `related_name='reservations'`.
  - `quantity`: `PositiveIntegerField`.
  - `expires_at`: `DateTimeField`.
  - `status`: `CharField(max_length=20)`, choices active/expired/converted, default active.
  - `created_at`: `DateTimeField(auto_now_add=True)`.

- Relationships:
  - User can have many reservations.
  - Ticket type can have many reservations.

- Methods and behavior:
  - `is_active` property returns true only when status is active and not expired by time.

- Integrity and lifecycle implications:
  - Expired-by-time reservations stop affecting dynamic availability queries.
  - Management command updates stale active rows to expired for lifecycle clarity.

---

## 3) Inter-app architecture and coupling details

- Accounts -> Events/Tickets authorization:
  - `organizer_required` in accounts is reused by organizer views in events and tickets.

- Accounts -> global user-role assumptions:
  - User creation signal in accounts underpins `request.user.profile` usage across all apps.

- Events -> Tickets capacity envelope:
  - `Event.allocated_capacity` is the upper budget that total ticket tiers must respect.

- Events status -> Tickets reservation service:
  - Ticket reservation service allows reservations only for published events.

- Events views <-> Tickets models:
  - Organizer event detail uses ticket-tier aggregate functions to show used/remaining capacity.

- Tickets operational workflow:
  - Expiration command supports reservation lifecycle and keeps state explicit over time.

---

## 4) Practical runtime flow summary

1. User signs up -> Profile role is set and persisted.
2. Organizer creates venues/events -> capacity checks run in model clean and signals.
3. Organizer creates ticket tiers -> tier totals are validated against event allocation.
4. Public sees only published events.
5. Attendee adds to cart -> transactional reservation service creates expiring holds.
6. Availability updates dynamically from sold + active holds.
7. Expiration command moves stale active reservations to expired status.

This architecture provides layered integrity (form, model, signal, DB constraint, and service transaction boundaries) around ticket inventory and capacity planning.
