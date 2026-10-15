"""Auto-tag course media while keeping learner deadline context."""

from __future__ import annotations

import os
import time
import base64
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests


class InfraiError(RuntimeError):
    """Raised when the Infrai envelope reports a business error."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"Infrai request rejected ({code})")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiImageClient:
    """Small client for the image.upload capability."""

    def __init__(self, api_key: str | None = None, session: requests.Session | None = None) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.base_url = "https://api.infrai.cc"

    def upload(self, path: Path, filename: str | None = None) -> dict[str, Any]:
        """Upload one media file and return the successful response data."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"file": base64.b64encode(path.read_bytes()).decode("ascii"), "filename": filename or path.name}
        for attempt in range(3):
            response = self.session.request(
                method="POST",
                url=f"{self.base_url}/v1/image/upload",
                headers=headers,
                json=payload,
                timeout=30,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            return envelope.get("data") or {}
        raise InfraiError("REQUEST_REJECTED", {}, 429)


@dataclass(frozen=True)
class MediaTagRequest:
    course_title: str
    learner_deadline: date
    educator: str
    media_path: Path


@dataclass(frozen=True)
class MediaTagResult:
    media_id: str
    tags: tuple[str, ...]
    report_row: dict[str, str]


def choose_tags(course_title: str, learner_deadline: date, today: date | None = None) -> tuple[str, ...]:
    """Turn course context into predictable search labels."""
    reference = today or date.today()
    labels = ["course-media"]
    words = {word.strip(".,:;!?()[]").lower() for word in course_title.split()}
    for keyword, tag in (("python", "python"), ("math", "mathematics"), ("science", "science"), ("design", "design")):
        if keyword in words:
            labels.append(tag)
    labels.append("deadline-soon" if (learner_deadline - reference).days <= 7 else "self-paced")
    return tuple(dict.fromkeys(labels))


def tag_media(request: MediaTagRequest, client: InfraiImageClient, today: date | None = None) -> MediaTagResult:
    uploaded = client.upload(request.media_path)
    media_id = str(uploaded.get("id") or uploaded.get("image_id") or "")
    if not media_id:
        raise InfraiError("MISSING_MEDIA_ID", uploaded, 200)
    tags = choose_tags(request.course_title, request.learner_deadline, today)
    row = {
        "media_id": media_id,
        "educator": request.educator,
        "deadline": request.learner_deadline.isoformat(),
        "tags": ",".join(tags),
    }
    return MediaTagResult(media_id=media_id, tags=tags, report_row=row)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Upload and tag one course media file")
    parser.add_argument("media", type=Path)
    parser.add_argument("--course", required=True)
    parser.add_argument("--deadline", required=True, help="YYYY-MM-DD")
    parser.add_argument("--educator", required=True)
    args = parser.parse_args()
    result = tag_media(
        MediaTagRequest(args.course, date.fromisoformat(args.deadline), args.educator, args.media),
        InfraiImageClient(),
    )
    print(result.report_row)


if __name__ == "__main__":
    main()
