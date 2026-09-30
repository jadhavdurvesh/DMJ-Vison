# DMJ Continuity Mesh (DCM)

**DMJ Continuity Mesh** is the project name for a topology-first, non-biometric method of proposing that two anonymous camera tracks may represent a continuous journey through an authorized site.

It is not facial recognition, person identification, or proof that two sightings belong to the same person. DCM creates **handoff propositions** for operator review and analytics, and deliberately preserves uncertainty.

## Definitions

| Term | Definition |
| --- | --- |
| **Continuity Mesh** | The directed graph of approved camera-to-camera travel routes in a site. |
| **Link window** | The minimum and maximum plausible travel time for one directed route. |
| **Evidence braid** | The bounded signals combined for a proposition: route validity, travel-time fit, direction agreement, observation quality, and detection confidence. |
| **Handoff proposition** | A scored, explainable suggestion that a predecessor track can plausibly continue into a target track. |
| **Review tier** | A score label (`weak`, `possible`, or `review`) that communicates how much human review is warranted; it never means “verified.” |
| **Topology gate** | The hard rule that disallows candidates outside configured routes, even if their timing seems plausible. |

## v0 scoring model

DCM first applies the topology gate and link window. It then computes a bounded score:

```text
score = 0.35 route validity
      + 0.25 travel-time fit
      + 0.20 mean observation quality
      + 0.15 mean detector confidence
      + 0.05 direction compatibility
```

Only candidates that pass the route and time gates are returned. The service returns its evidence components alongside the score so an operator can understand *why* it was proposed.

## Why it suits low-resolution systems

Low-resolution deployments cannot responsibly assume a reliable face signal. DCM makes the physical layout part of the model: a person can only move through realistic, configured paths in realistic times. This makes the system useful even when crops are small, lighting changes, or faces are unavailable.

## Guardrails

- Do not attach names, face templates, or identity labels to DCM tracks.
- Treat every proposition as an analyst cue, not a fact or an automated enforcement trigger.
- Configure only lawful, authorized camera routes; log every review.
- Set short retention periods and delete expired events/media automatically in a production storage adapter.
- Measure false-link and missed-link rates with authorized site footage before relying on results operationally.

## Future DCM adapters

1. A persistent topology store with versioned site maps and route approvals.
2. A calibration workflow that learns travel-time distributions while preserving conservative bounds.
3. A review queue that lets operators accept/reject propositions and feeds aggregate calibration metrics—not identity profiles.
4. A durable event store, RBAC, SSO, immutable audit exports, and retention workers.
