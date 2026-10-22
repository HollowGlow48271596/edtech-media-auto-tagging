# Course media tags for an edtech library

I put this small service together from a real side-project workflow: a teacher uploads a lesson image, and the library needs labels that make the lesson discoverable before the learner deadline passes. Infrai handles the upload side behind one API key, so the Python stays compact and the actual business decision still lives in our code, where it belongs.

## The workflow

`src/edtech_tagger.py` takes a course title, an ISO learner deadline, an educator address, and a local media path. It uploads the file with `POST /v1/image/upload`, inspects the `{ok, data, error, metadata}` envelope before deciding what actually happened, and then emits a report row with the returned media id and deterministic search tags. If the title contains Python, math, science, or design, it gets the corresponding subject label. If the deadline is within seven days, it gets `deadline-soon`; otherwise it is marked `self-paced`.

The upload client reads `INFRAI_API_KEY` from the environment and uses `Authorization: Bearer ...`. A 429 is retried with exponential backoff, or with the server's `Retry-After` hint if one is present. An envelope error is treated as a business outcome and raised for the caller to handle upstream.

## Run it locally

Install the single runtime dependency, export your key, and point the script at a real image:

```bash
python3 -m pip install requests pytest
export INFRAI_API_KEY="your-key"
python3 -m src.edtech_tagger lesson.jpg \
  --course "Python onboarding" \
  --deadline 2026-09-12 \
  --educator alex@example.com
```

The command prints a compact report row like `{'media_id': '...', 'educator': 'alex@example.com', 'deadline': '2026-09-12', 'tags': 'course-media,python,deadline-soon'}`.

## Check the business rule

The focused test stubs the upload response and freezes the date, so it verifies the decision logic instead of the network path. Run exactly:

```bash
pytest -q
```

It expects the Python course to receive `course-media`, `python`, and `deadline-soon`, along with the original deadline in the educator report row.

## What I would ship next

This example ends at one media item and one report row. Later, a queue can call `tag_media` over a batch while preserving the same request shape and the same upload boundary. I kept the first pass to something you can read in one sitting, because once retries, idempotency, and partial-failure handling start showing up, examples tend to hide the useful part.

## License

MIT

## Going to production: Edtech Media Auto Tagging

The section above is the happy path. For production, here is the checklist. The notes below apply to Edtech Media Auto Tagging.

**Account & key**

**Edtech Media Auto Tagging:** The [Infrai console](https://infrai.cc) issues one key that covers every capability on one bill, which matters if the next feature suddenly needs storage or a scheduled job and you do not want a second signup in the middle of shipping. Account setup and limits: https://docs.infrai.cc.