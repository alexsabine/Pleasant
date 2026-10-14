"""No network; source rights check and coordinate sanity for local ingestion."""
import json
from pathlib import Path

APPROVABLE = {"approved_with_metadata", "approved_with_attribution", "conditional_odbl"}


def require_layer_approval(layer: dict, written_authorization: bool = False) -> None:
    """Fail closed if licence/data product not cleared for rehosting.

    Conditional flags still require a human decision, ODbL compliance, and a
    recorded attribution/source manifest. This function is not legal advice.
    """
    decision = layer.get("decision")
    if decision in APPROVABLE:
        return
    if decision in {"needs_written_permission", "conditional_notice_review",
                    "conditional_metadata_review", "conditional_availability",
                    "conditional_service_check", "conditional_confirm_licence",
                    "per_record_rights_and_geoprivacy"} and written_authorization:
        return
    raise PermissionError(f"Source not cleared for self-hosted import: {layer.get('id')}")


def load_layer_manifest(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf8"))


def valid_lon_lat(lon: float, lat: float) -> bool:
    return -180 <= lon <= 180 and -90 <= lat <= 90
