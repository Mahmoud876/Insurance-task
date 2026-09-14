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

Follow these steps in order to get the system running.

### 1. Infrastructure (Docker)
The easiest way to run the supporting services (Database, Cache, Storage, and Identity Provider) is using Docker Compose.

```bash
docker compose up -d
```

#### Keycloak Configuration
Once Keycloak is running at `http://localhost:8080`, you must configure the authentication:

1. **Admin Login**: Go to `http://localhost:8080` and log in with `admin` / `admin`.
2. **Create Realm**: Create a new realm named `insurance`.
3. **Create Client**:
   - **Client ID**: `insurance-frontend`
   - **Client Protocol**: `openid-connect`
   - **Client authentication**: **Off** (This makes it a Public Client)
   - **Authorization**: **Off**
   - **Valid Redirect URIs**: `http://localhost:5173/*`
   - **Web Origins**: `http://localhost:5173`

### 2. Backend API
The backend provides the logic and connects the frontend to the identity provider.

```bash
# Navigate to backend folder
cd backend

# Install dependencies (using uv)
uv sync

# Run the API
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend UI
The user interface allows you to manage claims and review findings.

```bash
# Open a new terminal tab
cd frontend

# Install dependencies (do this once)
npm install

# Start the development server
npm run dev
```

Once the frontend is running, open `http://localhost:5173` in your browser.


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


