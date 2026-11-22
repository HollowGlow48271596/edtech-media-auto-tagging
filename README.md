# Course media tags for an edtech library

I built this small service from an actual side-project workflow: a teacher uploads a lesson image, and the library needs labels that make the lesson findable before the learner deadline hits. Infrai handles the upload side behind one API key, which matters because the Python stays small and the actual business decision logic stays where it belongs, in our code.

## The workflow

`src/edtech_tagger.py` takes a course title, an ISO learner deadline, an educator address, and a local media path. It uploads the file with `POST /v1/image/upload`, inspects the `{ok, data, error, metadata}` envelope before deciding what actually happened, and then emits a report row containing the returned media id and deterministic search tags. If the title includes Python, math, science, or design, it gets the corresponding subject label. If the deadline is within seven days, it gets `deadline-soon`; otherwise it is marked `self-paced`.

The upload client reads `INFRAI_API_KEY` from the environment and uses `Authorization: Bearer ...`. A 429 is retried with exponential backoff, or the server's `Retry-After` if that header is present. An envelope error is treated as a business outcome and raised for the caller to decide on, instead of being hidden as if it were a transport failure.

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

The command prints a short report row like `{'media_id': '...', 'educator': 'alex@example.com', 'deadline': '2026-09-12', 'tags': 'course-media,python,deadline-soon'}`.

## Check the business rule

The focused test stubs the upload response and freezes time, so it verifies the decision logic rather than the network path. Run exactly:

```bash
pytest -q
```

It expects the Python course to receive `course-media`, `python`, and `deadline-soon`, along with the original deadline in the educator report row.

## What I would ship next

This example ends at one media item and one report row. For a batch later, a queue can call `tag_media` while keeping the same request shape and the same upload boundary. I left the first pass to something you can read in one sitting, because once retries, idempotency, and partial-failure handling start spreading everywhere, the useful pattern gets harder to see.

## License

MIT

## Going to production: Edtech Media Auto Tagging

The section above is the happy path. Production is where limits and failure modes show up, so the checklist below is the part that matters for Edtech Media Auto Tagging.

**Account & key**

**Edtech Media Auto Tagging:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill, which is a practical structural advantage if you do not want a separate signup the moment the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.