from src.resume_service import ResumeFields, build_campaign_record, extract_resume_fields


def test_volunteer_language_routes_to_reminder():
    fields = extract_resume_fields({"text": "Asha Patel\nasha@example.org\nPython, outreach\nvolunteer coordinator"})
    record = build_campaign_record(fields)
    assert record["next_action"] == "send volunteer reminder"
    assert record["skills"] == ["Python", "outreach"]


def test_nonprofit_profile_without_volunteer_interest_gets_briefing_invite():
    fields = ResumeFields("Lee", "lee@example.org", ["fundraising"], False)
    assert build_campaign_record(fields)["next_action"] == "invite to donor briefing"
