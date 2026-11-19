# User guide

TalkWiseAI analyzes recorded calls and meetings and turns them into summaries, sales insights, tasks and reports. This guide follows the pages in the sidebar.

## Roles

| Role | Can |
|---|---|
| Agent | Upload recordings; see and work with the conversations they uploaded, their own tasks and their own performance; use the AI Copilot and knowledge base |
| Manager | Everything an agent can, for the whole team; team analytics and leaderboard; generate reports; sync PBX calls and test integrations |
| Admin | Everything a manager can; add and deactivate team members and change roles; configure integrations; manage the knowledge base; view the audit log |

## Signing in

Sign in with your email and password, or use **Create one** to start a new workspace (you become its admin). **Forgot password?** sends a reset link that works for 30 minutes. Your session renews itself while you use the app.

## Dashboard

An overview of the selected period: conversations, high-intent leads, open and overdue tasks, average agent score, sentiment, top objection, processing status, daily volume, sales intent, objections and topics. Use the filters at the top to change the date range, conversation type and (for managers and admins) team member. The small badges show the change against the previous period of the same length.

## Conversations

**Upload** an audio or video recording (MP3, WAV, M4A, OGG, FLAC, MP4, MOV, MKV, WEBM). Processing runs in the background and the page shows its progress; you also get a notification when it finishes.

Open a conversation to see:

- **Insights**: summary, key topics, decisions, sentiment, intent, pain points, objections, competitors and recommended next actions.
- **Transcript**: the full text with timestamps and talk-time per speaker. Speaker labels are inferred, so use **Rename speakers** to fix them.
- **Sales**: lead score, purchase intent, deal health, buying signals, budget and timeline.
- **Actions**: tasks the AI found.
- **Agent Score**: an AI-generated quality assessment with strengths and coaching notes. Treat it as one input among many.
- **Meeting Minutes**: formal minutes (download or copy them from the Meetings page).
- **CRM Updates**: changes the AI proposes for your CRM. Review, edit, then approve or reject; nothing is written until you approve.
- **Ask AI**: questions about this conversation, answered with citations.

**Follow-up email** drafts an email you can edit, copy or open in your mail app; it's never sent automatically. **Reprocess** runs the analysis again (for example after an AI key is added). **Delete** removes the recording and everything derived from it.

## Meetings

Every conversation with generated minutes. Switch to **Meetings only** to hide calls. Managers and admins can **Import recordings** from the connected meeting platform (currently a mock with two sample meetings). Click a card to read the minutes, download them as Markdown, copy them, or open the conversation.

## Sales Intelligence and Leads

**Sales Intelligence** shows deals as cards by pipeline stage (New, Contacted, Qualified, Demo, Proposal, Negotiation, Won, Lost) with lead score, intent, deal health and the next recommended action.

**Leads** is a table of the same deals with filters for score, intent and deal health. Change a lead's stage from the table when the deal moves; the change is recorded in the audit log.

## Action Items

Tasks from analyzed conversations plus your own. Filter by status, tick a task to complete it, or use the pencil to change the owner, due date, priority or status. Tasks past their due date are marked **Overdue**. **Add Task** creates a task that isn't linked to a conversation.

## AI Copilot

Ask questions across your conversations and the knowledge base, for example "What do customers say about pricing?". Answers cite their sources; if the answer isn't in your data, the Copilot says so.

Questions about numbers get exact answers with a table computed from your data, for example "How many high-intent leads did we have this month?", "What percentage of calls were positive?", "Which sales representative had the highest average score?", "Which customers mentioned competitors?" or "What are the top three objections in sales calls?". You can name a period (today, this week, last month, the last 14 days, this year) or a conversation type (sales calls, support calls, meetings).

## Knowledge Base

Company documents (pricing sheets, playbooks, FAQs) the Copilot can answer from. Admins upload PDF, DOCX, TXT or MD files with a category and can remove them.

## Analytics

Deeper trends for the selected filters: sentiment over time, objection frequency and resolution, the team leaderboard (AI-generated scores), pipeline stages and deal health, competitor mentions and call duration.

## Reports

Managers and admins generate executive, conversation, sales, agent performance, customer sentiment and objection reports for the last day, week, month or quarter. Reports are saved; open them from **Saved reports** and download them as PDF, CSV or Markdown. Everyone can export the conversations they can see as CSV.

## Team

Managers see the team with each person's role, conversation count and last sign-in. Admins can **Add member** (with a temporary password to share), change roles, and deactivate or reactivate accounts.

## Integrations

Status of the TalkWisely PBX, meeting platform (Zoom, Google Meet, Teams), CRM, calendar and email connections. They currently use mock adapters, which the page labels clearly. Managers and admins can **Test connection** and **Sync TalkWisely Calls**; admins can **Configure** each integration (turn it on or off and edit its settings).

## Settings and Profile

**Settings** holds your preferences, which are saved to your account:

- **Automatic Action Item Extraction**: save tasks the AI finds in your uploads.
- **Real-Time Lead Intent Alerts**: notify you when one of your conversations scores 80 or more.
- **TalkWisely Cloud PBX Auto-Sync**: import new PBX calls every 15 minutes.

Managers and admins also see which AI models are active, and admins see the audit log.

**Profile** lets you change your name and password.
