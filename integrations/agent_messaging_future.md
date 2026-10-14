# Optional stage-two agent and notifications

## Tool allow-list
First pilot: `search_published_resources`, `search_events`, `get_public_map_feature`, `explain_source_and_freshness`. Drafting tools can be enabled with authorized login; publishing remains human-approved. The model must not run unrestricted SQL, execute arbitrary code, access private records, or use bulk external API searches by default.

## Message sequence
User: 'Tell Amanda and Carol where I will be today.' -> resolve named opt-in contacts -> present disclosed **planned venue/time** not continuous GPS -> show exact message and channel -> user confirms -> permitted delivery -> record sent/delivered/pending status. Never impersonate user's phone; WhatsApp messages originate from a registered Business number, subject to Meta policy and country-based template restrictions. Google, SMS and WhatsApp are separate optional providers.

Second user: 'Tell everyone the weekend events.' -> check canonical event revision + announcement ID + recipients + delivery statuses -> if already sent say so; if changed, propose targeted update. Use database uniqueness/idempotency and transaction locks; LLM memory is not a sufficient duplicate guard.

## Children and urgent matters
No messaging individual children by default. No covert location sharing, emergencies or safeguarding decisions delegated to model. Escalate serious matters through human-approved paths.

## WhatsApp and cost
External account verification, opt-in and templates may be required; pricing/service eligibility changes. Do not include in Kim's base acceptance without separate agreement.
