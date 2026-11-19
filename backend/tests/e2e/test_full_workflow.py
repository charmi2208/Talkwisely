"""
End-to-end workflow from docs/SPEC.md §61, through the HTTP API with mock providers:

login -> upload recording -> transcription -> AI analysis -> view insights ->
create follow-up -> generate email -> approve CRM update
(plus speaker renaming, Copilot questions, reprocessing and deletion).
"""

from tests.conftest import upload


async def test_sales_call_workflow(client, agent):
    # Upload: processing runs to completion before the response returns (background task)
    conversation_id = await upload(client, agent, "E2E discovery call with Acme")

    status = (await client.get(f"/api/v1/conversations/{conversation_id}/processing-status", headers=agent)).json()
    assert status["conversation_status"] == "completed", status
    assert status["job"]["progress"] == 100

    # Transcript with speakers and talk-time stats
    transcript = (await client.get(f"/api/v1/conversations/{conversation_id}/transcript", headers=agent)).json()
    assert len(transcript["segments"]) > 5
    assert transcript["speakers"], "diarized speakers should be stored"
    stats = transcript["speaker_stats"]
    assert stats and abs(sum(s["talk_share"] for s in stats) - 1) < 0.01

    # Rename a speaker everywhere in the transcript
    first_label = stats[0]["label"]
    renamed = await client.patch(
        f"/api/v1/conversations/{conversation_id}/speaker-labels",
        headers=agent,
        json={"renames": {first_label: "Dana (Customer)"}},
    )
    assert renamed.status_code == 200
    assert "Dana (Customer)" in {s["speaker_label"] for s in renamed.json()["segments"]}

    # Every insight the acceptance criteria list
    insights = (await client.get(f"/api/v1/conversations/{conversation_id}/insights", headers=agent)).json()
    assert insights["summary"]["executive_summary"]
    assert insights["summary"]["key_topics"]
    assert insights["sentiment"]["overall_sentiment"] in ("positive", "negative", "neutral", "mixed")
    assert insights["intent"]["primary_intent"]
    assert insights["pain_points"]
    assert insights["action_items"]
    assert insights["sales_insight"]["lead_score"] is not None
    assert insights["sales_insight"]["buying_signals"]
    assert insights["sales_insight"]["deal_health"]
    assert insights["objections"]
    assert any(e["type"] == "competitor" for e in insights["entities"])
    assert insights["recommendations"]
    assert insights["agent_score"]["overall_score"] is not None
    assert "AI-generated" in insights["agent_score"]["disclaimer"]
    assert insights["meeting_minutes"]["formatted_markdown"].startswith("# Meeting Minutes")

    # Create a follow-up task linked to the call
    task = await client.post(
        "/api/v1/action-items",
        headers=agent,
        json={"conversation_id": conversation_id, "description": "Send the security whitepaper", "due_date": "2099-01-31"},
    )
    assert task.status_code == 201, task.text
    assert task.json()["conversation_title"] == "E2E discovery call with Acme"

    # Generate a follow-up email (draft only, never sent)
    email = await client.post(
        "/api/v1/ai/generate-email",
        headers=agent,
        json={"conversation_id": conversation_id, "email_type": "follow_up", "tone": "professional"},
    )
    assert email.status_code == 200, email.text
    assert email.json()["subject"] and email.json()["body"]

    # Review and approve the AI's CRM proposal
    proposals = (await client.get(
        "/api/v1/crm/proposals", headers=agent, params={"conversation_id": conversation_id}
    )).json()
    assert len(proposals) == 1 and proposals[0]["status"] == "pending"
    approved = await client.post(f"/api/v1/crm/proposals/{proposals[0]['id']}/approve", headers=agent, json={})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "applied"

    # Ask the Copilot about this conversation
    answer = await client.post(
        "/api/v1/ai/copilot/chat",
        headers=agent,
        json={"query": "What objections came up?", "conversation_id": conversation_id},
    )
    assert answer.status_code == 200
    assert answer.json()["answer"]

    # Completion notification
    notes = (await client.get("/api/v1/notifications", headers=agent)).json()
    assert any(n.get("conversation_id") == conversation_id for n in notes)

    # Reprocess replaces the results
    again = await client.post(f"/api/v1/conversations/{conversation_id}/reprocess", headers=agent)
    assert again.status_code == 200, again.text
    status = (await client.get(f"/api/v1/conversations/{conversation_id}/processing-status", headers=agent)).json()
    assert status["conversation_status"] == "completed"
    refreshed = (await client.get(f"/api/v1/conversations/{conversation_id}/insights", headers=agent)).json()
    assert len(refreshed["objections"]) == len(insights["objections"]), "old results must be replaced, not duplicated"

    # Delete removes the conversation
    assert (await client.delete(f"/api/v1/conversations/{conversation_id}", headers=agent)).status_code == 204
    assert (await client.get(f"/api/v1/conversations/{conversation_id}", headers=agent)).status_code == 404


async def test_upload_rejects_unsupported_files(client, agent):
    response = await client.post(
        "/api/v1/conversations/upload",
        headers=agent,
        files={"file": ("notes.exe", b"MZ", "application/octet-stream")},
        data={"title": "Not audio"},
    )
    assert response.status_code == 422
