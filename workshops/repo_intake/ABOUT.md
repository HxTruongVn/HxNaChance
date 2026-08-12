# Repository Intake & Review Workshop

This Workshop is the approval gate for external repositories entering NaChance. It performs static inspection in quarantine, produces an intake report, records resource claims and selects an integration mode. It never executes untrusted repository code during inspection.

The first implementation exposes the review domain service in `core/review/`. The desktop UI adapter is intentionally thin and should call the service rather than own intake policy.
