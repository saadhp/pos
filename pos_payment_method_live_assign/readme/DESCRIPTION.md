Allows POS managers to assign non-cash payment methods to Point of Sale
configurations even while sessions are currently open:

- Permits adding non-cash payment methods from POS Settings, Payment Method form, or
  the batch assignment wizard during open sessions.
- Preserves Odoo safety checks: cash payment methods cannot be added and existing
  payment methods cannot be removed while a session is open.
- Logs each live assignment on the open session chatter and pushes a WebSocket event
  so active POS screens refresh payment methods without reloading.
