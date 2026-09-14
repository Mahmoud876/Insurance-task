# ADR 002: Declarative Rules Engine

## Status
Accepted

## Context
Insurance rules change frequently based on policy updates and regulatory requirements. Hard-coding these rules into Python functions would require a full deployment cycle for every minor change.

## Decision
We implemented a **Declarative Rules Engine**. 

Rules are defined as JSON payloads (data) rather than code. The engine parses these declarations and applies the corresponding logic to the claim data. The rules are stored in the `ruleset_version` table in the database.

## Consequences
### Pros
- **Zero-Deploy Updates**: Rules can be updated via the UI and take effect immediately.
- **Auditability**: Every version of the rule set is stored, allowing the business to see exactly which rules were active at any point in time.
- **Empowerment**: Non-technical users (analysts) can potentially manage rules via the Admin UI.

### Cons
- **Performance Overhead**: Parsing JSON and applying generic logic is slightly slower than executing native Python code.
- **Complexity**: Building a generic engine that can handle a wide variety of rule types is more complex than writing a simple `if/else` block.
