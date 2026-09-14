# Demo Script: Claims Management System

## Goal
Demonstrate the end-to-end lifecycle of a claim: from creation and automated validation (scrubbing) to remediation of findings and final submission, concluding with the impact on analytics.

## Roles
- **Presenter**: Guides the flow and explains the "why".
- **Operator**: (Optional) Performs the actions in the UI.

---

## Scene 1: The Operational Overview (Dashboard)
**Action**: Start on the `/dashboard` page.
- **Presenter**: "Welcome. We'll start here on the Analytics Dashboard. This is the heartbeat of our operations. We can see the Status Funnel, which tells us exactly where our claims are in the pipeline—from draft to paid. Currently, our Clean Rate is [X]%, meaning [X]% of our claims are submitted without errors."
- **Key Point**: Highlight the "Top Findings" section to show common pain points in the current data.

## Scene 2: Creating a New Claim
**Action**: Navigate to `/claims` $\rightarrow$ Click **"New claim"**.
- **Presenter**: "Now, let's create a new claim. I'll enter the Patient, Provider, and Payer IDs. Notice how the system ensures we have the essential header data before we move to the clinical details."
- **Action**: Fill in header details and click **"Save changes"**.
- **Action**: Add a few procedure lines.
    - *Example*: Add a procedure code like `D7110` (Extraction).
    - *Note*: Intentionally omit a required narrative or attachment to trigger findings later.
- **Presenter**: "I'm adding a few procedures. I'll deliberately leave out a clinical narrative for this extraction, as our payer policy requires one for this specific code."

## Scene 3: Automated Validation (The Scrub)
**Action**: Navigate back to the `/claims` list.
- **Presenter**: "Instead of manually reviewing every field, we use the 'Bulk Scrub' feature. I'll select our new claim and trigger the scrubbing process."
- **Action**: Select the claim $\rightarrow$ Click **"Bulk scrub"**.
- **Presenter**: "The system is now running our rule engine against this claim, checking for clinical and financial inconsistencies."

## Scene 4: The Findings Workbench (Remediation)
**Action**: Open the claim in the editor.
- **Presenter**: "Here is the Findings Workbench. We can see the Readiness Score has dropped because of the missing narrative. The findings are grouped by severity. An 'ERROR' must be resolved before we can submit."
- **Action**: Show the `NARRATIVE_REQUIRED` finding.
    - **Option A (Apply Fix)**: "For some findings, the system suggests a safe correction. I'll click 'Apply fix' here."
    - **Option B (Override)**: "Sometimes, a finding is a false positive. I'll click 'Override' and document the clinical reason why this narrative isn't required in this specific case."
- **Action**: Resolve all ERROR findings.
- **Presenter**: "As we resolve the issues, you'll notice the Readiness Score increasing in real-time."

## Scene 5: Submission
**Action**: Click the **"Submit"** button (now active).
- **Presenter**: "Now that the claim is 'clean' and the readiness score is high, the Submit button is active. One click, and it's sent to the payer."
- **Action**: Confirm submission.

## Scene 6: Closing the Loop (Analytics)
**Action**: Return to the `/dashboard`.
- **Presenter**: "Finally, we return to the dashboard. Our status funnel has updated, and our submission metrics now reflect this successful, clean claim. This closed-loop system ensures higher first-pass acceptance rates and faster reimbursement."

---

## Discussion Points / Q&A
- "How are rules updated?" (Mention the rule engine in the backend).
- "Can we integrate with existing EHRs?" (Discuss API capabilities).
- "What happens if a claim is rejected by the payer?" (Explain the rejection flow back into the Workbench).
