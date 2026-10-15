from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.edtech_tagger import MediaTagRequest, tag_media


class FakeClient:
    def upload(self, path: Path) -> dict[str, str]:
        return {"id": "img_demo_123"}


def test_deadline_and_course_subject_drive_search_tags(tmp_path: Path) -> None:
    media = tmp_path / "lesson.jpg"
    media.write_bytes(b"demo")
    result = tag_media(
        MediaTagRequest("Python onboarding", date(2026, 9, 12), "alex@example.com", media),
        FakeClient(),
        today=date(2026, 9, 8),
    )
    assert result.media_id == "img_demo_123"
    assert result.tags == ("course-media", "python", "deadline-soon")
    assert result.report_row["deadline"] == "2026-09-12"
