# DMJ Continuity Mesh (DCM)

DMJ Continuity Mesh is a topology-first, non-biometric method of proposing that two anonymous camera tracks may represent a continuous journey through an authorized site.

It is not facial recognition, person identification, or proof that two sightings belong to the same person. DCM creates handoff propositions for operator review and analytics, and deliberately preserves uncertainty.

## v0 scoring model

DCM first applies the topology gate and travel-time window. It then computes:

    score = 0.35 route validity
          + 0.25 travel-time fit
          + 0.20 mean observation quality
          + 0.15 mean detector confidence
          + 0.05 direction compatibility

Direction compatibility is route-specific: each configured route defines allowed source and target direction values. The direction component is positive only when both observations satisfy that route configuration.

Only candidates that pass the route and time gates are returned. Evidence is returned alongside the score so an operator can inspect the basis of the proposition.

## Guardrails

- Do not attach names, face templates, or identity labels to DCM tracks.
- Treat every proposition as an analyst cue, not a fact or automated enforcement trigger.
- Configure only lawful, authorized camera routes; log every review.
- Set short retention periods and delete expired events/media automatically in production.
- Measure false-link and missed-link rates with authorized representative footage before operational reliance.

## Future DCM work

1. Persist and version site topology and route approvals.
2. Add calibration for conservative travel-time distributions.
3. Add a review queue for accept/reject decisions and aggregate quality metrics.
4. Add durable storage, RBAC, SSO, immutable audit exports, and retention workers.
