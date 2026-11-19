# Integration guide

TalkWiseAI connects to four kinds of external systems through adapters. Every adapter has an interface and a mock implementation; real providers are listed but not built yet, because their APIs (in particular TalkWisely's) aren't available to this project. The spec rule is to never invent a third-party API.

| Integration | Interface | Implemented provider | Used for |
|---|---|---|---|
| TalkWisely Cloud PBX | `CallProviderAdapter` (`integrations/talkwisely/talkwisely_adapter.py`) | Mock PBX: two sample call records with placeholder audio | Importing call recordings as conversations |
| CRM | `CRMProvider` (`integrations/crm/crm_adapter.py`) | Mock CRM: accepts writes without contacting anything | Writing approved CRM update proposals |
| Calendar | `CalendarProvider` (`integrations/calendar/calendar_adapter.py`) | Mock calendar | Scheduling follow-ups (adapter only; no UI yet) |
| Email | `EmailProvider` (`integrations/email_provider/email_adapter.py`) | Mock email: reports success without sending anything | Password reset emails; follow-up emails stay drafts |

## Configuration

Each organization has one row per integration in the `integrations` table, created with mock defaults the first time it's read (`integrations/registry.py`). Admins change them on the **Integrations** page or with `PUT /api/v1/integrations/{key}`:

- **Enabled**: when off, the adapter isn't used. Turning the CRM off blocks proposal approval; turning the PBX off blocks imports.
- **Provider**: only available providers can be selected; planned ones are shown as "Adapter not implemented yet".
- **Settings**: only the non-secret fields declared in the registry (for example "Calls per sync" for the PBX, "CRM display name"). Values are validated and range-checked.

Credentials never go in the database or through the API. Real adapters read them from environment variables (`docs/SETUP.md`).

**Test connection** (`POST /api/v1/integrations/{key}/test`) runs the adapter's `health_check()` and reports the time it took. The mock adapters say plainly that nothing external was contacted.

## TalkWisely PBX import

`POST /api/v1/integrations/talkwisely/sync` (admins and managers), the **Sync TalkWisely Calls** button, and the optional auto-sync all call `services/pbx_import.py`:

1. Fetch up to "Calls per sync" recent calls from the adapter.
2. Skip calls already imported (tracked by call ID in the stored file name).
3. Save each recording, create a conversation with the call metadata (caller, PBX agent, call type), and queue it for analysis like an upload.
4. Record the sync time and an audit entry.

Because the mock PBX has no real audio, imports are refused unless `STT_PROVIDER=mock`, with a message explaining why. Users who turn on **TalkWisely Cloud PBX Auto-Sync** in Settings get an import every `PBX_AUTO_SYNC_INTERVAL_MINUTES` (default 15) for their organization.

## CRM approval flow

1. The CRM update agent proposes field changes after each analysis (`crm_records`, status `pending`).
2. On the conversation's **CRM Updates** tab, a person reviews, optionally edits, and approves or rejects.
3. Approval calls the CRM adapter (`update_lead` or `update_opportunity`), then marks the proposal `applied`, records who approved it, updates the integration's last sync time and writes an audit entry. A failed write leaves the proposal pending.

## Adding a real provider

Example: HubSpot for the CRM.

1. Implement the interface in `integrations/crm/`, for example `HubSpotCRMProvider(CRMProvider)`, reading its key from settings (`HUBSPOT_API_KEY` already exists in `core/config.py`). Implement `health_check()` with a cheap authenticated call.
2. Return it from `get_crm_provider()` in `api/v1/crm.py` when `integration.provider == "hubspot"`.
3. Add it to `check_connection()` in `integrations/registry.py`.
4. Mark the provider `available=True` in the `INTEGRATIONS` registry and add any non-secret settings as `ConfigField`s.
5. Add tests that mock the HTTP calls (`httpx` makes this straightforward) and update this guide.

The same steps apply to the PBX (implement `fetch_calls`, `fetch_call_recording`, `fetch_call_metadata`), calendar and email adapters.
