# ADR 001: Modular Monolith Architecture

## Status
Accepted

## Context
We needed to build a claims processing system with several distinct domains: Identity/Auth, Claims Management, Rule Engine, Scrubbing, and Analytics. The team had to choose between a Microservices architecture and a Monolith.

## Decision
We adopted a **Modular Monolith** architecture. 

The application is a single deployable unit, but the internal code is strictly partitioned into modules (e.g., `/app/modules/claims`, `/app/modules/rules`). Each module has its own internal service layer and models, and communication between modules is managed through clearly defined internal APIs.

## Consequences
### Pros
- **Simplified Deployment**: Only one container to manage and scale.
- **Lower Complexity**: No need for distributed tracing, complex service discovery, or network overhead between services.
- **Type Safety**: Internal boundaries are enforced via Python typing and folder structure, providing a balance between speed and structure.
- **Easier Refactoring**: Moving logic between modules is a local code change rather than a cross-service API change.

### Cons
- **Resource Contention**: All modules share the same CPU/Memory pool.
- **Single Point of Failure**: A critical crash in one module can potentially bring down the entire process (mitigated by robust error handling).
