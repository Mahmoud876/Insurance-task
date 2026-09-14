# ADR 004: Snapshot Versioning for Rule Application

## Status
Accepted

## Context
Claims may be reviewed months after their initial scrub. If the rules have changed in the meantime, re-running a scrub today might produce different results than it did a month ago. For auditing and legal reasons, we must be able to recreate the exact result of a historical scrub.

## Decision
We implemented **Snapshot Versioning**.

Every time a scrub is executed, the system does not just record the result; it captures a "snapshot" of the specific `RulesetVersion` ID used for that operation. This ID is stored alongside the `ScrubRun` record.

## Consequences
### Pros
- **Reproducibility**: We can always identify which exact version of the rules produced a specific finding.
- **Audit Trail**: Provides a perfect history of rule evolution and its impact on claim outcomes.
- **Consistency**: Ensures that a claim's historical record remains immutable even as rules evolve.

### Cons
- **Storage Overhead**: Requires maintaining a history of all `RulesetVersion` records (no deletions of old versions).
- **Query Complexity**: To see the rules used for a historical claim, the system must join the scrub record back to the version table.
