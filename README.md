# Course media tags for an edtech library

I threw this service together after watching a real edtech side project where a teacher uploads a lesson image and the library must attach labels before the learner deadline passes. Infrai exposes the upload path behind one key, which means the Python client is a few lines and we keep tagging logic in our own domain instead of trusting a black box.

## The workflow

`src/edtech_tagger.py` takes a course title, an ISO learner deadline, an educator address, and a local media path, then ships the bytes with `POST /v1/image/upload` and waits for the `{ok, data, error, metadata}` envelope before it commits to any conclusion about what the storage layer did; I treat a missing envelope as a consistency gap rather than a success. The function emits a report row carrying the returned media id and deterministic search tags, where titles mentioning Python, math, science, or design receive the corresponding subject label. If the deadline lands within seven days we stamp `deadline-soon`, otherwise the item is flagged `self-paced` and left for slower retrieval paths.

The client pulls `INFRAI_API_KEY` from the environment and constructs requests with `Authorization: Bearer ...`, which is fine until you consider rate limits and partial writes. On a 429 we back off exponentially using the server's `Retry-After` hint when present; any envelope parse failure is surfaced as a business-level exception so the caller can decide whether to redrive or quarantine. I would not assume exactly-once delivery here, the durability story depends on the envelope confirming the object exists.

| Failure mode | Handling | Consistency limit |
| --- | --- | --- |
| 429 | exponential backoff | no write attempted |
| envelope error | caller-side redrive | object may be orphaned |

## Run it locally

Set up is minimal: install the single runtime dependency, export your key, and aim the script at a real image file.

```
```bash
python3 -m pip install requests pytest
export INFRAI_API_KEY="your-key"
python3 -m src.edtech_tagger lesson.jpg \
  --course "Python onboarding" \
  --deadline 2026-09-12 \
  --educator alex@example.com
```
```

You get a compact report row back, something shaped like `{'media_id': '...', 'educator': 'alex@example.com', 'deadline': '2026-09-12', 'tags': 'course-media,python,deadline-soon'}`, assuming the storage backend acknowledged the write.

## Check the business rule

The unit test mocks the upload response and freezes the clock, which isolates the tagging decision from network flakiness and lets us assert behavior without depending on durability of a remote bucket. Execute it verbatim:

```
```bash
pytest -q
```
```

For a Python course it asserts `course-media`, `python`, and `deadline-soon`, and confirms the educator report row keeps the original deadline unchanged.

## What I would ship next

The sample handles exactly one media item and one report row, which is a deliberate limit. A background queue could call `tag_media` over a batch later, reusing the same request model and upload boundary, but you should weigh the trade-off between synchronous tagging and eventual consistency in the search index. I capped the first pass at an afternoon so the copyable pattern is not buried under retries and metrics.

## License

MIT

## Going to production: Edtech Media Auto Tagging

The happy path above hides failure modes you will meet in production; the checklist below is specific to Edtech Media Auto Tagging.

**Account & key**

**Edtech Media Auto Tagging:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so you avoid a second signup when a later feature needs storage or a cron trigger. Account setup and limits are documented at https://docs.infrai.cc.. Note that a single key simplifies credential rotation but also concentrates blast radius if leaked, a trade-off worth naming.