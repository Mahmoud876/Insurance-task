# Operational Runbook: InsureFlow

This runbook provides standard operating procedures for managing the InsureFlow claims processing system.

## 🚀 Deployment & Rollback

### Deployment
For local development and testing:
1. Update the source code.
2. Run `docker compose up -d --build`.
3. Verify logs using `docker compose logs -f api`.

For production environments:
- Deployment is handled via the CI/CD pipeline.
- Images are built and pushed to the registry.
- Kubernetes/ECS orchestrator performs a rolling update.

### Rollback
If a deployment introduces a critical bug:
1. **Git Rollback**: Revert the commit on the main branch or checkout a previous known-good tag.
2. **Redeploy**: Trigger the CI/CD pipeline to deploy the reverted version.
3. **DB Migration**: If the failed deploy included a destructive DB migration, use Alembic to downgrade:
   `docker exec insurance-task-api-1 alembic downgrade -1`

---

## 🛠 Rule Management

### Publishing a Rule Set
Rules are managed via the Rules Admin interface:
1. Navigate to the **Rules** page.
2. Create or edit a rule set.
3. Save the rule set as a `draft`.
4. Select **Publish**. This sets the `status` to `published` and records the `published_at` timestamp in the `ruleset_version` table.

### Disabling a Misbehaving Rule (No Deploy)
Since rules are stored as JSON payloads in the database, they can be modified without a code change:
1. Use the Rules Admin UI to edit the current published rule set.
2. Remove or disable the specific rule within the JSON payload.
3. Publish a new version. The system will pick up the new rule set for subsequent scrubs.

---

## 🔄 Data Operations

### Re-running a Scrub
To re-evaluate claims against the latest rules:
1. Use the **Scrub** trigger in the UI or call the `/api/claims/{id}/scrub` endpoint.
2. The system will execute the scrub logic, update the claim status, and persist a new `ScrubRun` record.

### Restore from Backup
1. **Stop Application**: `docker compose stop api`.
2. **Restore DB**: 
   `docker exec insurance-task-postgres-1 psql -U postgres -d claims_db -f /path/to/backup.sql`
3. **Restart Application**: `docker compose start api`.

---

## 🚨 Escalation & Support

### Escalation Path
1. **L1 (On-call Engineer)**: First responder for alerts and critical crashes.
2. **L2 (Lead Backend/Frontend Engineer)**: Deep dive into logic bugs or infrastructure issues.
3. **L3 (Architect)**: Structural changes or critical security vulnerabilities.

### Known Limitations
- ** la-Scale migrations**: Large database migrations may cause temporary downtime.
- **Keycloak Dependency**: System is entirely dependent on the OIDC provider for identity.
- **Memory Limits**: High-volume scrub runs may put pressure on the API container's memory.

## 📈 Maintenance & Quality

### Rule Quality Review
On a periodic basis (e.g., end of development cycle), the team must review rule effectiveness:
1. Analyze the `dcs_rule_hits_total` metric.
2. **Retire**: Any rule that has never fired over a significant sample size.
3. **Retune**: Any rule that fires on >80% of claims, as it may be too broad to be useful.
