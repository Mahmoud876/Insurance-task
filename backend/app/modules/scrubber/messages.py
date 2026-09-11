RULE_MESSAGES: dict[str, str] = {
    "P4_POL_EXPIRED": "Insurance policy was expired on the service date ({service_date}). Policy expiration date: {expiration_date}.",
    "P4_POL_NOT_EFFECTIVE": "Insurance policy was not effective on the service date ({service_date}). Policy effective date: {effective_date}.",
    "P4_DEP_AGE_LIMIT": "Dependent age ({age}) exceeds maximum allowed coverage age limit ({age_limit}) under this policy.",
    "P4_WAITING_PERIOD": "Service date ({service_date}) falls within the mandatory waiting period ending on {waiting_period_end}.",
    "P4_ANNUAL_MAX_EXHAUSTED": "Annual maximum benefit limit (${annual_max}) has been exhausted for subscriber {member_id}.",
    "P4_CATEGORY_EXCLUSION": "Procedure code '{procedure_code}' belongs to category '{category}' which is excluded from coverage.",
    "P4_FREQ_LIMITATION": "Procedure '{procedure_code}' exceeds frequency limitation. Allowed: {allowed_count} per {period_months} months.",
    "P4_COB_ORDER": "Incorrect Coordination of Benefits (COB) order. Primary insurance must be billed before secondary payer '{payer_id}'.",
}
