# sentinel_core/session.py
# Authoritative session-state constants.
#
# A session is OPEN while it accepts requests. After close() it is CLOSED and
# any further request is refused with BLOCK_SESSION_CLOSED. ERROR is reserved
# for a session terminated by an unrecoverable persistence fault.

SESSION_OPEN = "OPEN"
SESSION_CLOSED = "CLOSED_BY_OPERATOR"
SESSION_ERROR = "CLOSED_BY_ERROR"

VALID_SESSION_STATES = frozenset({SESSION_OPEN, SESSION_CLOSED, SESSION_ERROR})
