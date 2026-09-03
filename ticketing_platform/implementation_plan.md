# V5 Implementation Plan: Bulk Import & Waitlists with Celery

## Goal Description

Implement the **Bulk Import & Waitlists** feature (V5) for the Tick-It ticketing platform:

- Organizers can upload a CSV file containing a list of VIP guests (name, email, optional ticket type).
- Uploaded guests are added to the event’s **waitlist** or directly allocated tickets if capacity permits.
- When a ticket is **refunded** or cancelled, the next user on the waitlist is automatically promoted and sent a notification/email.
- All background processing (CSV parsing, bulk ticket creation, waitlist promotion) will be off‑loaded to **Celery** workers to keep the request/response cycle fast and reliable.

## User Review Required

> [!IMPORTANT]
> Please review the following design decisions before we start implementation:
>
> - **CSV Format**: Columns expected – `email`, `full_name`, `ticket_type` (optional). Do you need any additional fields (e.g., phone, notes)?
> - **Email Notification**: Should the system send an email upon promotion from the waitlist? If yes, confirm the email template location or any branding requirements.
> - **Waitlist Model**: Do you want a separate `WaitlistEntry` model or reuse the existing `Ticket` model with a `status='waitlisted'` flag?
> - **Celery Broker**: The project currently uses Redis for caching; confirm if we should also use Redis as the Celery broker/backend (recommended) or another service.
> - **Admin UI**: Where should the CSV upload button live (event detail page, separate admin view)? Provide any UI mockup preferences.

## Open Questions

> [!WARNING]
> - **CSV Validation Rules**: How strict should validation be? Should the import abort on the first invalid row or skip/collect errors?
> - **Duplicate Handling**: If a CSV contains an email that already has a ticket or is already on the waitlist, should we ignore, update, or error?
> - **Promotion Timing**: Should promotion be immediate (synchronous) after a refund, or queued as a separate Celery task?
> - **Maximum Waitlist Size**: Any limit on how many users can be on the waitlist for an event?

## Proposed Changes

### 1. Models (`events/models.py`)
- **Add `WaitlistEntry` model** (or extend `Ticket` with `status='waitlisted'`). Fields:
  - `event` (FK to `Event`)
  - `user` (FK to `User` – optional, for registered users)
  - `email` (CharField)
  - `full_name` (CharField)
  - `ticket_type` (FK to `TicketType`, nullable)
  - `created_at` (DateTimeField auto_now_add)
  - `position` (IntegerField – computed order)
- **Add method `promote_next()`** on `Event` to promote the first `WaitlistEntry` when capacity frees up.
- **Signal**: Connect to `Ticket` deletion/refund to trigger promotion.

### 2. Celery Configuration (`ticketing_platform/celery.py` & `settings.py`)
- Create `celery.py` initializing Celery app with Redis broker/backend.
- Add `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to `settings.py`.
- Ensure Django app autodiscovers tasks (`app.autodiscover_tasks()`).
- Update `__init__.py` to import Celery.

### 3. Tasks (`events/tasks.py`)
- **`process_bulk_import(event_id, csv_content)`**: Parses CSV, creates `WaitlistEntry` objects, checks venue capacity, allocates tickets where possible, and enqueues promotion tasks.
- **`promote_waitlist_entry(entry_id)`**: Converts a waitlist entry into an actual `Ticket`, sends email, and marks entry as promoted.
- **`handle_refund(ticket_id)`**: Called when a ticket is refunded; deletes ticket, then calls `event.promote_next()` via Celery.

### 4. Views (`events/views.py`)
- Add a new view `BulkImportView` (class‑based, `FormView`) handling CSV file upload.
- The view validates the uploaded file, reads its content, and **dispatches** `process_bulk_import.delay(event.id, file.read().decode())`.
- Return a success page with a background “import in progress” message.
- Add URL pattern `path('events/<int:pk>/bulk_import/', BulkImportView.as_view(), name='event_bulk_import')`.

### 5. Forms (`events/forms.py`)
- `BulkImportForm` with a `FileField` limited to `text/csv` and max size (e.g., 5 MB).

### 6. Templates (`templates/jinja2/events/event_detail.html` or a new `bulk_import.html`)
- Add a **“Bulk Import VIP Guests”** button visible only to organizers.
- Render the `BulkImportForm` inside a modal or separate page.
- Include CSRF token (already handled globally).

### 7. Email Notifications (`events/email.py`)
- Function `send_waitlist_promotion_email(entry)` using Django’s email backend.
- Template `emails/waitlist_promotion.html`.

### 8. Admin & Permissions
- Restrict bulk import view to users with `organizer` role and event ownership (`event.organizer_id == request.user.id`).
- Add appropriate `@login_required` and custom permission checks.

### 9. Tests (`events/tests/test_bulk_import.py`)
- Unit tests for CSV parsing, capacity handling, waitlist creation.
- Integration test that a refund triggers promotion via Celery (use `celery.test` utilities or `CELERY_TASK_ALWAYS_EAGER = True`).

### 10. Documentation (`docs/bulk_import_waitlist.md`)
- Explain CSV format, workflow, and how to monitor Celery tasks (Flower dashboard).

---
## Verification Plan

### Automated Tests
- Run existing test suite plus new bulk‑import tests: `python manage.py test events`.
- Use `CELERY_TASK_ALWAYS_EAGER = True` in test settings to execute Celery tasks synchronously.

### Manual Verification
- As an organizer, upload a CSV with 5 VIP entries for an event that has only 3 free tickets.
- Verify that 3 tickets are allocated instantly and the remaining 2 appear in the waitlist order.
- Refund one of the allocated tickets and confirm that the first waitlisted entry receives a ticket and an email.
- Check Celery logs (`celery -A ticketing_platform worker -l info`) and Flower UI to ensure tasks are queued and completed.

---
**Next Steps**
- Once you approve the plan, I will start implementing the Celery setup, model changes, and bulk‑import view.
- Feel free to adjust any of the open questions or add further requirements.
