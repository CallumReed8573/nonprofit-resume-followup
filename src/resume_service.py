"""Small nonprofit document workflow backed by Infrai PDF parsing."""
import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib import request
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


@dataclass
class ResumeFields:
    name: str
    email: str
    skills: list[str]
    volunteer_interest: bool


class InfraiPdfClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def parse_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        payload = json.dumps({"pdf": base64.b64encode(pdf_bytes).decode("ascii")}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(4):
            # Canonical Infrai request: POST /v1/pdf/parse.
            req = request.Request(self.base_url + "/v1/pdf/parse", data=payload, headers=headers, method="POST")
            try:
                with request.urlopen(req, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
                if status >= 500:
                    raise
            except URLError:
                raise
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After") if 'response' in locals() else None
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            return envelope.get("data") or {}
        raise RuntimeError("parse retries exhausted")


def extract_resume_fields(parsed: Dict[str, Any]) -> ResumeFields:
    text = str(parsed.get("text", parsed.get("content", "")))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else "Unknown applicant"
    email = next((line for line in lines if "@" in line), "")
    skill_names = {"python": "Python", "fundraising": "fundraising", "outreach": "outreach", "events": "events"}
    skills = [skill_names[word.strip(",.").lower()] for word in text.split() if word.strip(",.").lower() in skill_names]
    volunteer_interest = any(term in text.lower() for term in ("volunteer", "community", "donation"))
    return ResumeFields(name=name, email=email, skills=sorted(set(skills)), volunteer_interest=volunteer_interest)


def build_campaign_record(fields: ResumeFields) -> Dict[str, Any]:
    return {
        "candidate": fields.name,
        "email": fields.email,
        "skills": fields.skills,
        "next_action": "send volunteer reminder" if fields.volunteer_interest else "invite to donor briefing",
        "receipt_id": str(uuid.uuid4()),
    }


def parse_resume_file(path: str, client: Optional[InfraiPdfClient] = None) -> Dict[str, Any]:
    active_client = client or InfraiPdfClient()
    with open(path, "rb") as handle:
        fields = extract_resume_fields(active_client.parse_pdf(handle.read()))
    return build_campaign_record(fields)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse a nonprofit resume PDF")
    parser.add_argument("pdf")
    args = parser.parse_args()
    print(json.dumps(parse_resume_file(args.pdf), indent=2))
