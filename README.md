# Dental Claim Scrubber

A rule-based system for validating dental insurance claims before submission to reduce claim denials, improve claim quality, and provide reproducible validation results.

> 🚧 **Project Status:** This project is currently under development.

---

## Overview

Dental Claim Scrubber validates dental insurance claims before they are submitted to an insurance provider. It helps identify common errors early, reducing claim denials and improving the accuracy and consistency of submitted claims.

---

## Features

- Rule-based claim validation
- Reproducible scrub runs
- React frontend for reviewing claim validation results
- Python backend API
- Audit trail for validation results
- Docker-based development environment

---

## Technology Stack

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui

### Backend

- Python
- PostgreSQL 16
- Redis 7
- MinIO

### Development Tools

- Docker Compose
- GitHub Actions
- ESLint
- Prettier
- Ruff
- MyPy
- Pytest

---

## Project Structure

```text
.
├── frontend/
├── backend/
├── docs/
├── .github/
├── docker-compose.yml
├── CONTRIBUTING.md
├── Makefile
└── README.md
```

---

## Prerequisites

Before running the project, make sure you have installed:

- Git
- Node.js
- Python 3.12+
- Docker Desktop (or Docker Engine with Docker Compose)

---

## Installation

Repository setup instructions will be added once the project structure is finalized.

```bash
git clone <repository-url>
cd <repository-name>
```

---

## Running the Project

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

Backend setup instructions will be added after the backend is implemented.

### Docker

```bash
docker compose up
```

---

## Development

Common development commands:

```bash
make dev
make build
make test
make lint
```

---

## Contributing

Please read **CONTRIBUTING.md** before creating branches or submitting Pull Requests.

---

## License

License information will be added by the project maintainers.