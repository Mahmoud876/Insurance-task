# Contributing Guide

Thank you for contributing to the Dental Claim Scrubber project.

Please follow the guidelines below when contributing to this repository to ensure consistency and maintain code quality.

---

# Branch Naming

Create a new branch for every task or bug fix.

Use the following naming convention:

- `feature/<short-description>` – New features
- `bugfix/<short-description>` – Bug fixes
- `docs/<short-description>` – Documentation changes
- `chore/<short-description>` – Maintenance tasks (configuration, dependencies, tooling)

### Examples

```text
feature/frontend-scaffold
feature/login-page
bugfix/fix-validation
docs/update-readme
chore/configure-eslint
```

---

# Commit Convention

Use **Conventional Commits** when writing commit messages.

### Format

```text
<type>: <short description>
```

### Common Types

| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation |
| refactor | Code restructuring without changing behavior |
| test | Add or update tests |
| chore | Maintenance or configuration changes |

### Examples

```text
feat: add frontend scaffold

fix: correct claim validation logic

docs: update contributing guide

test: add validator tests

chore: configure prettier
```

---

# Pull Request Checklist

Before opening a Pull Request, ensure all of the following are completed:

- [ ] Build succeeds.
- [ ] Lint passes.
- [ ] Tests pass.
- [ ] Documentation is updated if necessary.
- [ ] No secrets, passwords, or API keys are committed.
- [ ] Code follows the project's coding style.
- [ ] Self-review completed.

---

# Database Migration Rules

All database schema changes must be backward compatible.

Always follow this sequence:

1. Add the new column as **nullable**.
2. Deploy the migration.
3. Backfill existing records with valid data.
4. Update the application to use the new column.
5. Change the column to **NOT NULL** only after all existing data has been updated.

Avoid introducing breaking schema changes in a single deployment.

---

# Definition of Done

A task is considered complete only when all of the following conditions are met:

- [ ] Code is implemented.
- [ ] Project builds successfully.
- [ ] Lint passes.
- [ ] All tests pass.
- [ ] Documentation has been updated when necessary.
- [ ] No secrets are committed to the repository.
- [ ] Pull Request has been reviewed and approved.
- [ ] Changes are merged into the main branch.

