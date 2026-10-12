from datetime import datetime

from prices.models import PriceRecordingRun


def mark_recording_finished(finished_at: datetime) -> None:
    """Insert one price-recording run finished at this aware time."""
    PriceRecordingRun.objects.create(finished_at=finished_at)


def latest_recording_finished_at() -> datetime | None:
    """Return the newest finish time, or None when no run is stored.

    The newest row has the greatest ``finished_at``, then the greatest pk.
    """
    run = PriceRecordingRun.objects.order_by("-finished_at", "-pk").first()
    if run is None:
        return None
    return run.finished_at
