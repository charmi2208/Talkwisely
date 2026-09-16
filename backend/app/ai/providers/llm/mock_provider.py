"""
Mock LLM Provider — generates realistic AI outputs without API calls.

Used when LLM_PROVIDER=mock in .env. Produces deterministic, schema-valid
responses that make the platform fully demonstrable without a real API key.

When a real key is available, set LLM_PROVIDER=openai in .env.
"""

import json
import random
from datetime import datetime

from app.ai.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.core.logging import get_logger

logger = get_logger("mock_llm")


class MockLLMProvider(LLMProvider):
    """
    Realistic mock LLM responses for demonstration and testing.

    Responses are structured to match the expected JSON schemas of every agent,
    using plausible business conversation data.
    """

    def __init__(self) -> None:
        logger.info("Using MOCK LLM provider — set LLM_PROVIDER=openai for real AI")

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-gpt-4o"

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Return a mock completion response."""
        # Determine what type of response to return based on prompt content
        system_msg = next((m.content for m in messages if m.role == "system"), "")
        content = self._generate_mock_response(system_msg)

        return LLMResponse(
            content=content,
            model=self.model_name,
            input_tokens=500,
            output_tokens=300,
            finish_reason="stop",
        )

    async def complete_json(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Return a mock JSON response parsed from mock text."""
        system_msg = next((m.content for m in messages if m.role == "system"), "")
        return self._generate_mock_json(system_msg)

    def _generate_mock_response(self, system_prompt: str) -> str:
        """Choose appropriate mock response based on system prompt keywords."""
        prompt_lower = system_prompt.lower()
        if "copilot" in prompt_lower or "assistant" in prompt_lower:
            return (
                "Based on your recorded conversations and sales intelligence records:\n\n"
                "1. **Acme Corp** (Enterprise PBX Discovery Call): Discussed enterprise cloud migration, 200 seats pricing proposal ($25,000–$50,000 range), and CRM webhooks.\n"
                "2. **Nexus Telecom** (Contact Center Technical Review): Evaluated AI call analytics and virtual numbers integration.\n"
                "3. **Global Logistics**: High purchase intent for VoIP trunking & UK virtual numbers ($40,000+ budget).\n\n"
                "**Recommendation**: High-intent lead Acme Corp is awaiting proposal confirmation. Follow up by Friday."
            )
        mock = self._generate_mock_json(system_prompt)
        return json.dumps(mock, indent=2)

    def _generate_mock_json(self, system_prompt: str) -> dict:
        """Return structured mock data matching each agent's expected schema."""
        prompt_lower = system_prompt.lower()

        if "classif" in prompt_lower:
            return self._mock_classification()
        elif "summar" in prompt_lower:
            return self._mock_summary()
        elif "action item" in prompt_lower or "task" in prompt_lower:
            return self._mock_action_items()
        elif "sentiment" in prompt_lower:
            return self._mock_sentiment()
        elif "intent" in prompt_lower:
            return self._mock_intent()
        elif "pain point" in prompt_lower:
            return self._mock_pain_points()
        elif "sales" in prompt_lower and "intelligence" in prompt_lower:
            return self._mock_sales_insight()
        elif "objection" in prompt_lower:
            return self._mock_objections()
        elif "competitor" in prompt_lower or "entity" in prompt_lower:
            return self._mock_entities()
        elif "meeting minute" in prompt_lower:
            return self._mock_meeting_minutes()
        elif "email" in prompt_lower:
            return self._mock_email()
        elif "crm" in prompt_lower:
            return self._mock_crm_update()
        elif "recommend" in prompt_lower:
            return self._mock_recommendations()
        elif "qa" in prompt_lower or "performance" in prompt_lower or "score" in prompt_lower:
            return self._mock_agent_score()
        elif "transcript" in prompt_lower and "clean" in prompt_lower:
            return self._mock_cleaned_transcript()
        else:
            return {"result": "Mock AI response generated", "provider": "mock"}

    # ---- Individual mock data generators ----

    def _mock_classification(self) -> dict:
        return {
            "conversation_type": random.choice(["sales", "customer_support", "product_demo", "follow_up"]),
            "primary_purpose": "Enterprise software sales inquiry with pricing discussion",
            "participants": ["Sales Representative", "Customer (IT Director)"],
            "business_context": "B2B SaaS enterprise sales",
            "confidence": 0.92,
        }

    def _mock_summary(self) -> dict:
        return {
            "executive_summary": (
                "A 28-minute sales call between our sales representative and the IT Director "
                "of Meridian Financial Group. The customer expressed strong interest in the enterprise "
                "communication platform, specifically requesting information on API integrations and "
                "pricing for a 200-seat deployment. The call ended with a commitment to schedule "
                "a technical demo next week."
            ),
            "detailed_summary": (
                "The call opened with introductions and a brief discussion of the customer's "
                "current telephony challenges, including high costs from their legacy PBX and "
                "lack of call analytics. The sales representative presented the platform overview "
                "and highlighted AI call analytics, CRM integration, and the cloud PBX solution. "
                "The customer raised questions about Salesforce integration, data security (SOC 2 compliance), "
                "and pricing for 200 seats. Pricing was discussed at a high level (enterprise tier). "
                "The customer expressed interest in seeing a live demo with the CRM integration shown. "
                "The call concluded with next steps: technical demo scheduled for Thursday."
            ),
            "key_topics": [
                "Legacy PBX migration",
                "AI call analytics",
                "Salesforce CRM integration",
                "SOC 2 compliance & data security",
                "Enterprise pricing (200 seats)",
                "Technical demo scheduling",
            ],
            "decisions": [
                "Schedule technical demo for Thursday at 2 PM",
                "Sales rep to send enterprise pricing proposal by EOD Wednesday",
            ],
            "important_moments": [
                {"timestamp": 180.0, "description": "Customer reveals current spend of $8,000/month on legacy PBX"},
                {"timestamp": 720.0, "description": "Customer confirms 200-seat deployment target"},
                {"timestamp": 1380.0, "description": "Customer requests SOC 2 compliance documentation"},
                {"timestamp": 1620.0, "description": "Demo scheduled — strong positive buying signal"},
            ],
            "open_questions": [
                "Does the customer need HIPAA compliance in addition to SOC 2?",
                "What CRM fields need to sync with the call analytics dashboard?",
            ],
            "next_steps": [
                "Send enterprise pricing proposal by Wednesday EOD",
                "Confirm demo for Thursday 2 PM",
                "Share SOC 2 compliance documentation",
                "Connect customer with technical architect for integration questions",
            ],
        }

    def _mock_action_items(self) -> dict:
        return {
            "action_items": [
                {
                    "description": "Send enterprise pricing proposal for 200-seat deployment",
                    "owner": "Sales Representative",
                    "owner_speaker": "Speaker 1",
                    "due_date": "Wednesday EOD",
                    "priority": "high",
                    "related_topic": "Pricing",
                    "timestamp": 1580.0,
                },
                {
                    "description": "Share SOC 2 compliance documentation and security whitepaper",
                    "owner": "Sales Representative",
                    "owner_speaker": "Speaker 1",
                    "due_date": "Before Thursday demo",
                    "priority": "high",
                    "related_topic": "Security",
                    "timestamp": 1420.0,
                },
                {
                    "description": "Confirm technical demo appointment for Thursday 2 PM",
                    "owner": "Sales Representative",
                    "owner_speaker": "Speaker 1",
                    "due_date": "Today",
                    "priority": "urgent",
                    "related_topic": "Demo scheduling",
                    "timestamp": 1640.0,
                },
                {
                    "description": "Evaluate API integration requirements with internal IT team",
                    "owner": "Customer (IT Director)",
                    "owner_speaker": "Speaker 2",
                    "due_date": "Before demo",
                    "priority": "medium",
                    "related_topic": "API Integration",
                    "timestamp": 890.0,
                },
            ]
        }

    def _mock_sentiment(self) -> dict:
        return {
            "overall_sentiment": "positive",
            "overall_score": 0.72,
            "customer_sentiment": "mostly_positive",
            "agent_sentiment": "positive",
            "sentiment_trend": "Neutral → Interested → Positive",
            "timeline": [
                {"timestamp": 0.0, "speaker": "Speaker 2", "sentiment": "neutral", "score": 0.1},
                {"timestamp": 300.0, "speaker": "Speaker 2", "sentiment": "curious", "score": 0.35},
                {"timestamp": 700.0, "speaker": "Speaker 2", "sentiment": "interested", "score": 0.6},
                {"timestamp": 1380.0, "speaker": "Speaker 2", "sentiment": "slightly_concerned", "score": 0.4},
                {"timestamp": 1500.0, "speaker": "Speaker 2", "sentiment": "satisfied", "score": 0.75},
                {"timestamp": 1640.0, "speaker": "Speaker 2", "sentiment": "positive", "score": 0.8},
            ],
            "positive_moments": [
                {"timestamp": 720.0, "description": "Customer excited about AI analytics capabilities"},
                {"timestamp": 1640.0, "description": "Customer enthusiastically agrees to demo"},
            ],
            "negative_moments": [
                {"timestamp": 1100.0, "description": "Customer expresses concern about implementation timeline"},
            ],
            "frustration_detected": False,
            "satisfaction_detected": True,
        }

    def _mock_intent(self) -> dict:
        return {
            "primary_intent": "purchase_intent",
            "secondary_intents": ["pricing_inquiry", "demo_request", "integration_request"],
            "confidence": 0.88,
            "evidence": [
                {"text": "We're looking to replace our entire phone system this quarter", "timestamp": 145.0},
                {"text": "Can you send me the pricing for 200 seats?", "timestamp": 720.0},
                {"text": "I'd love to see it in action with our Salesforce setup", "timestamp": 1520.0},
            ],
        }

    def _mock_pain_points(self) -> dict:
        return {
            "pain_points": [
                {
                    "category": "financial",
                    "description": "Paying $8,000/month for legacy PBX with no analytics or intelligence",
                    "severity": "high",
                    "desired_outcome": "Reduce costs while gaining AI-powered analytics",
                    "potential_solution": "Cloud PBX with AI call analytics at competitive enterprise pricing",
                    "evidence": "We're spending $8,000 a month and getting zero insights from our phone calls",
                    "timestamp": 180.0,
                },
                {
                    "category": "operational",
                    "description": "No visibility into call quality or agent performance",
                    "severity": "high",
                    "desired_outcome": "Real-time and historical call analytics with agent scoring",
                    "potential_solution": "AI conversation intelligence with agent performance dashboard",
                    "evidence": "Our managers have no idea what's happening on customer calls",
                    "timestamp": 290.0,
                },
                {
                    "category": "technical",
                    "description": "Legacy system does not integrate with Salesforce CRM",
                    "severity": "medium",
                    "desired_outcome": "Bi-directional CRM sync with automatic call logging",
                    "potential_solution": "Native Salesforce integration with automatic opportunity updates",
                    "evidence": "Our reps have to manually update Salesforce after every call",
                    "timestamp": 850.0,
                },
            ]
        }

    def _mock_sales_insight(self) -> dict:
        return {
            "lead_score": 82,
            "purchase_intent": "high",
            "deal_health": "healthy",
            "budget_discussed": True,
            "budget_range": "$8,000–$12,000/month",
            "decision_maker_present": True,
            "timeline_discussed": True,
            "timeline": "Q3 this year (within 3 months)",
            "buying_signals": [
                {
                    "signal": "Customer mentions specific deployment size (200 seats)",
                    "timestamp": 720.0,
                    "evidence": "We need this for about 200 people across our offices",
                },
                {
                    "signal": "Committed to scheduling technical demo",
                    "timestamp": 1620.0,
                    "evidence": "Yes, let's do Thursday at 2 — I'll block it in my calendar",
                },
                {
                    "signal": "Decision maker (IT Director) is directly engaged",
                    "timestamp": 0.0,
                    "evidence": "Customer introduced themselves as IT Director with budget authority",
                },
            ],
            "upsell_opportunities": [
                "AI-powered IVR and intelligent call routing",
                "WhatsApp Business integration",
            ],
            "cross_sell_opportunities": [
                "Contact centre solution for their support team",
            ],
            "stage": "demo",
            "closing_probability": 0.73,
        }

    def _mock_objections(self) -> dict:
        return {
            "objections": [
                {
                    "category": "security",
                    "description": "Customer concerned about data security and compliance",
                    "exact_quote": "We handle financial data, so we need to know about SOC 2 compliance",
                    "timestamp": 1380.0,
                    "severity": "medium",
                    "was_resolved": True,
                    "suggested_response": "Confirm SOC 2 Type II certification and share compliance documentation. Offer to connect with security team.",
                },
                {
                    "category": "timing",
                    "description": "Customer worried about implementation timeline disrupting operations",
                    "exact_quote": "How long does migration take? We can't have any downtime",
                    "timestamp": 1100.0,
                    "severity": "medium",
                    "was_resolved": True,
                    "suggested_response": "Explain phased migration approach with zero-downtime cutover. Share migration timeline documentation.",
                },
            ]
        }

    def _mock_entities(self) -> dict:
        return {
            "entities": [
                {"type": "competitor", "value": "RingCentral", "context": "Customer mentioned evaluating RingCentral", "timestamp": 960.0, "sentiment": "neutral", "mention_count": 2},
                {"type": "competitor", "value": "8x8", "context": "Customer previously trialed 8x8", "timestamp": 975.0, "sentiment": "slightly_negative", "mention_count": 1},
                {"type": "product", "value": "Salesforce", "context": "Customer requires CRM integration", "timestamp": 850.0, "sentiment": "positive", "mention_count": 3},
                {"type": "technology", "value": "API", "context": "Customer wants REST API access", "timestamp": 890.0, "sentiment": "neutral", "mention_count": 2},
                {"type": "company", "value": "Meridian Financial Group", "context": "Customer's organization", "timestamp": 5.0, "sentiment": "neutral", "mention_count": 1},
                {"type": "plan", "value": "Enterprise Tier", "context": "Pricing tier discussed", "timestamp": 720.0, "sentiment": "positive", "mention_count": 2},
            ]
        }

    def _mock_meeting_minutes(self) -> dict:
        return {
            "objective": "Sales discovery call to understand requirements and present TalkWiseAI platform capabilities",
            "participants_summary": "Sales Representative (TalkWiseAI), IT Director (Meridian Financial Group)",
            "discussion_points": [
                "Current telephony challenges: legacy PBX, high costs, no analytics",
                "TalkWiseAI platform overview: Cloud PBX, AI analytics, CRM integration",
                "API integration capabilities and Salesforce connector",
                "Data security, SOC 2 compliance, and financial data handling",
                "Enterprise pricing for 200-seat deployment",
                "Implementation timeline and migration approach",
            ],
            "decisions": [
                "Technical demo scheduled for Thursday at 2:00 PM",
                "Enterprise pricing proposal to be sent by Wednesday EOD",
            ],
            "action_items_summary": [
                "Sales Rep: Send enterprise pricing proposal — Wednesday EOD",
                "Sales Rep: Share SOC 2 compliance documentation — Before Thursday",
                "Sales Rep: Confirm demo calendar invite — Today",
                "Customer: Review API integration requirements internally — Before demo",
            ],
            "open_questions": [
                "HIPAA compliance requirements?",
                "Specific Salesforce fields for bi-directional sync?",
                "Number of office locations for deployment?",
            ],
            "risks": [
                "Customer is evaluating RingCentral — competitive risk",
                "Security/compliance documentation must be strong",
            ],
            "next_steps": [
                "Send pricing proposal by Wednesday",
                "Send compliance documentation",
                "Technical demo Thursday 2 PM",
                "Post-demo: technical architecture review with IT team",
            ],
            "next_meeting": "Technical Demo — Thursday 2:00 PM",
        }

    def _mock_email(self) -> dict:
        return {
            "subject": "Thank you for your time — TalkWiseAI Demo Confirmed for Thursday",
            "body": (
                "Dear [Customer Name],\n\n"
                "Thank you for taking the time to speak with us today. It was great to learn more about "
                "Meridian Financial Group's communication challenges and your goals for this quarter.\n\n"
                "As discussed, I'm confirming our technical demo for Thursday at 2:00 PM. "
                "During the session, we'll walk through:\n\n"
                "• Live AI call analytics and conversation intelligence\n"
                "• Salesforce CRM bi-directional integration\n"
                "• Cloud PBX migration approach for your 200-seat deployment\n"
                "• SOC 2 compliance architecture\n\n"
                "I'm also attaching:\n"
                "• Enterprise pricing proposal (200 seats)\n"
                "• SOC 2 Type II compliance documentation\n"
                "• Implementation timeline and migration guide\n\n"
                "Please don't hesitate to reach out if you have any questions before Thursday.\n\n"
                "Looking forward to the demo!\n\n"
                "Best regards,\n"
                "[Sales Representative Name]\n"
                "TalkWiseAI\n"
            ),
            "tone": "professional",
            "email_type": "demo_confirmation",
        }

    def _mock_crm_update(self) -> dict:
        return {
            "crm_entity_type": "lead",
            "proposed_changes": {
                "lead_stage": {"from": "contacted", "to": "qualified"},
                "purchase_intent": {"from": "unknown", "to": "high"},
                "deal_size_estimate": {"from": None, "to": "$8,000–$12,000/month"},
                "next_action": {"from": None, "to": "Technical Demo"},
                "next_action_date": {"from": None, "to": "Thursday"},
                "notes": "IT Director confirmed 200-seat deployment interest. High buying intent. Demo scheduled.",
                "lead_score": {"from": None, "to": 82},
            },
            "reasoning": "Customer demonstrated strong purchase intent, confirmed budget authority, and committed to demo.",
        }

    def _mock_recommendations(self) -> dict:
        return {
            "recommendations": [
                {
                    "category": "demo",
                    "action": "Run technical demo focused on Salesforce integration and AI analytics",
                    "reasoning": "Customer explicitly requested CRM integration demo and AI analytics walkthrough",
                    "priority": "urgent",
                    "urgency": "this_week",
                    "evidence": ["Customer confirmed demo for Thursday", "Salesforce integration is top requirement"],
                },
                {
                    "category": "proposal",
                    "action": "Send enterprise pricing proposal for 200-seat deployment by Wednesday EOD",
                    "reasoning": "Customer asked for specific pricing. Budget is confirmed (~$8k/month existing spend).",
                    "priority": "high",
                    "urgency": "today",
                    "evidence": ["Customer asked: Can you send me the pricing for 200 seats?"],
                },
                {
                    "category": "competitive",
                    "action": "Prepare competitive battlecard against RingCentral and 8x8",
                    "reasoning": "Customer mentioned evaluating both competitors. Address differentiators proactively.",
                    "priority": "medium",
                    "urgency": "before_demo",
                    "evidence": ["Customer mentioned RingCentral evaluation", "Previously trialed 8x8"],
                },
            ]
        }

    def _mock_agent_score(self) -> dict:
        return {
            "overall_score": 84,
            "greeting_score": 90,
            "professionalism_score": 88,
            "empathy_score": 82,
            "listening_score": 85,
            "question_quality_score": 80,
            "product_knowledge_score": 90,
            "objection_handling_score": 78,
            "closing_score": 85,
            "talk_ratio": 0.52,
            "interruption_count": 2,
            "filler_word_count": 8,
            "strengths": [
                "Excellent product knowledge — answered technical questions confidently",
                "Clear and structured presentation of platform capabilities",
                "Successfully secured commitment for technical demo",
                "Professional tone maintained throughout",
            ],
            "weaknesses": [
                "Could have asked more discovery questions earlier in the call",
                "Security objection could have been handled more proactively",
                "Slightly high talk ratio — allow customer more speaking time",
            ],
            "improvement_suggestions": [
                "Use SPIN selling framework for deeper discovery before presenting features",
                "Pre-empt security/compliance objections with proactive SOC 2 mention",
                "Practice listening more — pause 2 seconds before responding",
            ],
            "coaching_notes": "Strong call overall. Agent secured a high-quality demo with a verified decision maker. Focus on improving discovery depth and security objection handling in next coaching session.",
            "disclaimer": "This is an AI-generated assessment and should be reviewed alongside direct observation and context. AI assessments are one input, not a definitive evaluation.",
        }

    def _mock_cleaned_transcript(self) -> dict:
        return {
            "language": "en",
            "cleaned": True,
            "segment_count": 45,
            "topics_identified": ["pricing", "crm_integration", "security", "demo_scheduling"],
            "artifacts_removed": 3,
        }
