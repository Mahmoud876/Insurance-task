# User Guide: Claims Management System

## Overview
The Claims Management System is designed to streamline the process of creating, validating, and submitting insurance claims. It ensures that claims are clinically and financially accurate before submission to reduce rejection rates.

## Claim Lifecycle

### 1. Creating a Claim
- Navigate to the **Claims** page.
- Click the **"New claim"** button.
- In the **Claim Editor**, fill in the required header information:
    - **Patient ID**: Unique identifier for the patient.
    - **Provider ID**: The dental provider performing the service.
    - **Payer ID**: The insurance company.
    - **Service Dates**: The date range when the service was provided.
- Add line items (procedures) using the **"Add line"** button. For each line, specify:
    - **Procedure Code**: Search for the correct code (e.g., D0120).
    - **Tooth Number/Surface**: Specify the location of the procedure.
    - **Charge Amount**: The fee for the procedure.
- Click **"Save changes"** to store the claim as a draft.

### 2. Validating (Scrubbing) a Claim
Scrubbing is an automated process that checks the claim against clinical and financial rules.
- From the **Claims** list, select one or more claims using the checkboxes.
- Click the **"Bulk scrub"** button.
- The system will update the **Readiness Score** and generate a list of **Findings**.

### 3. The Findings Workbench
The Findings Workbench in the Claim Editor helps you remediate issues.
- **Findings**: Grouped by severity (ERROR, WARNING, INFO).
- **Remediation**:
    - **Apply fix**: Automatically correct the field to a recommended value.
    - **Go to field**: Quickly jump to the field requiring attention.
    - **Override**: If a finding is a false positive or clinically justified, click "Override" and provide a reason.
- **Readiness Score**: Your goal is to reach a high readiness score by resolving all ERROR findings.

### 4. Submitting the Claim
- Once all ERROR findings are resolved or overridden, the **"Submit"** button becomes active.
- Click **"Submit"** and confirm the action.
- The claim status will change from `DRAFT` to `SUBMITTED`.

## Analytics Dashboard
The dashboard provides a high-level view of operations:
- **Status Funnel**: Tracks claims moving through DRAFT $\rightarrow$ SUBMITTED $\rightarrow$ ACCEPTED/REJECTED $\rightarrow$ PAID.
- **Clean Rate**: Percentage of claims submitted without errors.
- **Top Findings**: Identifies common errors to help improve provider documentation.
- **Category Breakdown**: Shows which types of errors (Financial, Documentation, etc.) are most frequent.
