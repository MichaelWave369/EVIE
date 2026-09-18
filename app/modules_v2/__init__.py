"""Internal v2 generator implementations.

These are kept verbatim (as much as possible) and are invoked through the
v1 runtime via adapter wrappers in app.modules.*.

IMPORTANT: Do not import registry or modules here to avoid import-time
side effects / optional dependency issues.
"""