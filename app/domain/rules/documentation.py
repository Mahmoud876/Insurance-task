from .findings import RuleFinding
from .models import RuleClaim


RADIOGRAPH_REQUIRED = "RADIOGRAPH_REQUIRED"
NARRATIVE_REQUIRED = "NARRATIVE_REQUIRED"
PRE_AUTHORISATION_REQUIRED = "PRE_AUTHORISATION_REQUIRED"


def check_radiograph_required(claim: RuleClaim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    has_radiograph = any(
        attachment.file_type.lower() in {
            "image/jpeg",
            "image/jpg",
            "image/png",
            "jpeg",
            "jpg",
            "png",
            "application/pdf",
            "pdf",
        }
        for attachment in claim.attachments
    )

    for line in claim.lines:
        requirements = claim.procedure_requirements.get(line.procedure_code)

        if requirements is None or not requirements.requires_radiograph:
            continue

        if not has_radiograph:
            findings.append(
                RuleFinding(
                    code=RADIOGRAPH_REQUIRED,
                    message=(
                        f"Procedure {line.procedure_code} requires "
                        "a radiograph attachment."
                    ),
                    field_name="attachments",
                    raw_value=None,
                )
            )

    return findings


def check_narrative_required(claim: RuleClaim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    has_narrative = bool(claim.narrative and claim.narrative.strip())

    for line in claim.lines:
        requirements = claim.procedure_requirements.get(line.procedure_code)

        if requirements is None or not requirements.requires_narrative:
            continue

        if not has_narrative:
            findings.append(
                RuleFinding(
                    code=NARRATIVE_REQUIRED,
                    message=(
                        f"Procedure {line.procedure_code} requires "
                        "a narrative."
                    ),
                    field_name="narrative",
                    raw_value=claim.narrative,
                )
            )

    return findings


def check_pre_authorisation_required(
    claim: RuleClaim,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    requires_authorisation = any(
        requirements.requires_pre_authorisation
        for requirements in claim.procedure_requirements.values()
    )

    if not requires_authorisation:
        return findings

    if not claim.authorization_number or not claim.authorization_number.strip():
        findings.append(
            RuleFinding(
                code=PRE_AUTHORISATION_REQUIRED,
                message=(
                    "Pre-authorisation is required but no "
                    "authorisation number was provided."
                ),
                field_name="authorization_number",
                raw_value=claim.authorization_number,
            )
        )

    return findings