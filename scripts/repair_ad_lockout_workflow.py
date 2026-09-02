from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings
from app.storage import JarvisStore
from app.workflow_templates import AD_ACCOUNT_LOCKOUT_IMPLEMENTATION


def main() -> int:
    settings = get_settings()
    store = JarvisStore(settings.database_path)
    store.initialize()
    matches = [item for item in store.get_workflows() if item.title.casefold() == "ad account lockouts"]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one active AD Account Lockouts workflow; found {len(matches)}.")
    revised = store.revise_workflow_implementation(
        matches[0].id,
        AD_ACCOUNT_LOCKOUT_IMPLEMENTATION,
        actor="A.E.G.I.S.-9 maintenance",
        reason="Correct service-account filtering, domain-controller event correlation, unlock timing, bounded execution, and structured UI output",
    )
    if revised is None:
        raise RuntimeError("The workflow is active or otherwise unavailable for a safe revision.")
    print(f"Workflow {revised.id} moved to {revised.state} at revision {revised.revision}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
