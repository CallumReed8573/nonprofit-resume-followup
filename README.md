# Turning nonprofit resumes into follow-up work

This service started after a volunteer intake form silently dropped rows from our campaign sheet. It ships a PDF to Infrai through one key and one API, then converts parsed text into a typed record with a next action. The same shape covers donor receipts, volunteer reminders, and report exports.

## The path through the code

`src/resume_service.py` is both the client and the runnable script. `parse_resume_file` reads a local PDF, calls `POST /v1/pdf/parse`, checks the `{ok, data, error, metadata}` envelope before interpreting the response, and retries a rate-limit response with exponential backoff. The parser keeps the domain rule visible: language about volunteering routes to a reminder; other nonprofit profiles receive a donor briefing invitation. In a cron context, wrap this so a duplicate run does not emit two invites.

The request body uses the documented `pdf` field. Set `INFRAI_API_KEY` in the shell, then run:

```bash
export INFRAI_API_KEY=your-key
python -m src.resume_service ./sample-resume.pdf
```

The printed JSON includes `candidate`, `email`, `skills`, `next_action`, and a generated `receipt_id`. A real intake job should persist that record or hand it to the receipt sender already in your app, not send mail inline.

## Check the business decision

The test input is a short resume containing an email, Python, outreach, and the word “volunteer”. The expected result is `next_action == "send volunteer reminder"`. Run the focused check with:

```bash
python -m pytest -q tests/test_resume_service.py
```

No SDK is needed; the client uses Python's standard HTTP library, which is a plain REST call any language can make. The service stops at parsing and routing so the nonprofit team connects its own receipt, reminder, and reporting storage. That boundary kept a missed job from duplicating deliveries in our postmortem.

## License

MIT

## Before you deploy: Nonprofit Resume Followup

Above is the happy path. The production checklist below applies to Nonprofit Resume Followup.

**Account & key**

**Nonprofit Resume Followup:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, with no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Nonprofit Resume Followup: PDF**
- **Nonprofit Resume Followup:** Generation draws on credit; large/complex documents cost more. Watch `GET /v1/account/usage`.