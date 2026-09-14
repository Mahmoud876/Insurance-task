from .findings import RuleFinding
from .models import RuleClaim


UNSUPPORTED_ATTACHMENT_TYPE = "UNSUPPORTED_ATTACHMENT_TYPE"
ATTACHMENT_SIZE_LIMIT = "ATTACHMENT_SIZE_LIMIT"

SUPPORTED_ATTACHMENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "pdf",
        "jpeg",
        "jpg",
        "png",
    }
)

MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024


def check_attachment_types(claim: RuleClaim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for index, attachment in enumerate(claim.attachments):
        normalized_type = attachment.file_type.strip().lower()

        if normalized_type not in SUPPORTED_ATTACHMENT_TYPES:
            findings.append(
                RuleFinding(
                    code=UNSUPPORTED_ATTACHMENT_TYPE,
                    message=(
                        f"Attachment type '{attachment.file_type}' "
                        "is not supported."
                    ),
                    field_name=f"attachments[{index}].file_type",
                    raw_value=attachment.file_type,
                )
            )

    return findings


def check_attachment_sizes(claim: RuleClaim) -> list[RuleFinding]:
    findings: list[RuleFinding] = []

    for index, attachment in enumerate(claim.attachments):
        if attachment.file_size is None:
            continue

        if attachment.file_size > MAX_ATTACHMENT_SIZE_BYTES:
            findings.append(
                RuleFinding(
                    code=ATTACHMENT_SIZE_LIMIT,
                    message=(
                        f"Attachment exceeds the maximum size of "
                        f"{MAX_ATTACHMENT_SIZE_BYTES} bytes."
                    ),
                    field_name=f"attachments[{index}].file_size",
                    raw_value=attachment.file_size,
                )
            )

    return findings
