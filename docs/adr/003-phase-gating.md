# ADR 003: Phase Gating in Claims Processing

## Status
Accepted

## Context
Claims move through a complex lifecycle (Draft $\rightarrow$ Scrubbed $\rightarrow$ Submitted $\rightarrow$ Paid/Denied). It is critical to ensure a claim does not skip essential quality checks (like the scrubbing phase) before being submitted to the payer.

## Decision
We implemented **Phase Gating**.

The claim lifecycle is modeled as a state machine. Transition to the next phase (e.g., "Submitted") is guarded by a "gate" that verifies the required criteria have been met (e.g., a successful scrub run with no critical errors).

## Consequences
### Pros
- **Quality Assurance**: Guarantees that only "clean" claims are submitted, reducing payer rejections.
- **Process Clarity**: The current phase provides an immediate status of where the claim is in the workflow.
- **Automation**: Gating allows for automated triggers (e.g., auto-submitting a claim once a scrub is clean).

### Cons
- **Rigidity**: Adding new phases requires updating the state machine and transition logic.
- **User Friction**: Users must resolve all errors before proceeding, which can be frustrating if the rules are too strict.
