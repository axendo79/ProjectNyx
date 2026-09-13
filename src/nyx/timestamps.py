"""Pure ingestion validation, independent of the writer's recording clock."""

from datetime import datetime


def validate_timestamp(value: str, field: str = "occurred_at") -> None:
    """ADR 0006 ingestion gate: require an instant without rewriting its bytes."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} not ISO8601") from exc
    if parsed.utcoffset() is None:
        raise ValueError(f"{field} must carry a timezone offset")
