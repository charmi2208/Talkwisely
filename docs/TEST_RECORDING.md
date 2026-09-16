# Test Recording Script

A short (30–45 second) mock sales call for testing the upload → transcription → AI analysis pipeline end to end. Record it with two voices (one person can play both roles), then upload it on the Conversations page.

It deliberately packs in a pain point, intent, buying signals, objections, action items and a follow-up, so most agents have something to detect.

## Script

**Sales Representative:** "Hi Alex, thanks for taking the time today. I wanted to show you our business communication platform. It provides cloud calling, call analytics, and CRM integration."

**Customer:** "Thanks. We're actually looking for something like this. Our biggest problem is that our sales team spends too much time manually reviewing calls."

**Sales Representative:** "That's something our AI call intelligence can help with. It can summarize conversations, identify customer intent, and generate follow-up tasks."

**Customer:** "That sounds useful. I'm mainly concerned about pricing and whether it can integrate with our existing CRM."

**Sales Representative:** "Absolutely. We support CRM integrations, and I can send you the enterprise pricing details after this call."

**Customer:** "Okay. Please send me the pricing and integration documentation. If everything looks good, we'd like to schedule a demo next week."

**Sales Representative:** "Perfect. I'll send both today and follow up with you next week."

## Expected results

| Insight | Expected |
|---|---|
| Conversation type | Sales call |
| Summary | Customer is interested in a business communication platform and is evaluating AI call intelligence |
| Purchase intent | High |
| Buying signals | Interested in the product; requested pricing; requested integration documentation; wants a demo |
| Pain point | Sales team spends significant time manually reviewing calls |
| Objections | Pricing; CRM integration |
| Action items | Send enterprise pricing; send CRM integration documentation; follow up next week; schedule demo |
| Recommended next action | Schedule a product demo and send pricing/integration documentation |
| Lead score | Roughly 80–90 / 100 |
| Sentiment | Positive |
| Timestamps | The pricing objection and demo request should point to the matching transcript segments |

These results only reflect the recording when real providers are enabled (`STT_PROVIDER=whisper_local` and a real `LLM_PROVIDER`). In mock mode, every upload returns the same canned transcript and analysis.
