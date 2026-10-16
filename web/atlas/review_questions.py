"""The 'Questions for Kim' page content: decisions only the organisation can make, each with
what is built today (so the answer can be tested against something real) and what the answer
would change. Plain data; the template renders it and the form stores replies as ReviewNote."""

QUESTIONS = [
    {
        "key": "onboarding",
        "title": "Onboarding: who can access the map, and who can add to it?",
        "ask": "Should the map stay open to anyone without an account, as now? Who should be allowed to add places: anyone through the moderated form, only people who have joined, or only named contributors a steward has approved?",
        "built": "Anyone can browse everything without an account. Joining is optional, asks for an adult confirmation and nothing about children, and every welcome step can be skipped. Anyone can suggest a place through the public form; nothing publishes until a steward checks it. A joined person can ask to become a contributor; a steward grants it by hand.",
        "changes": "Closing the map to members changes the public-access promise in your brief. Opening adding to everyone without review is already ruled out by the brief (submissions never auto-publish).",
    },
    {
        "key": "people",
        "title": "People mapping: should onboarding offer to link people in, with permission?",
        "ask": "Do you want people to be able to appear on the atlas at all, for example as a named contact for a programme, a volunteer steward, or a family that says 'we are new here too'? If so, who grants and withdraws that, and what is shown?",
        "built": "No person is mapped. Listings carry an organisation's public phone or website only. Accounts hold adult-chosen settings (age bands, budget, step-free, community) that never leave the account. The audit log records who verified what, by username, for stewards only.",
        "changes": "Any person-level presence needs explicit, revocable consent on the server, a coarse location at most (the H3 public ceiling is res 8, about 0.7 km² cells, with counts under five suppressed), and a decision about minors, who should never be linkable.",
    },
    {
        "key": "fog",
        "title": "Fog mode: reveal only the places you have been, like a game map?",
        "ask": "Would you like an optional 'fog' view where the map starts hidden and clears around places a person marks as visited, so the atlas becomes a record of their own exploring? Should it be personal only, or could families share a cleared map with each other?",
        "built": "Saved places exist (private to the account). The map already renders exact H3 cells per venue and a halo one grid step wide, which is the natural unit for clearing fog. No visit history is stored, and no location is read from the device.",
        "changes": "Fog can be built from saved places with no new data about where anyone actually went: a person marks a place as visited, and the cell clears. Automatic clearing from the phone's location is out, because the brief forbids covert location collection.",
    },
    {
        "key": "governance",
        "title": "Map governance: who decides how the whole resource changes over time?",
        "ask": "Adding a place and changing the system are different powers. Who should decide system-level change: the categories, the freshness constants, what Lumen is allowed to do, whether a new mode (fog, people, messaging) is switched on? One organisation, two named admins, a small council, or a monthly open review?",
        "built": "Steward accounts (the Moderators group), starting with the founding stewards Kim, Sasha, Daniel and Bill, approve publication and can edit the published constants without code changes. Editors draft and verify but cannot publish. Every publish, verification and Lumen answer is written to a hash-chained audit log that anyone with admin access can verify. The maths and policy are published in the repository.",
        "changes": "The proposal's monthly loop (listen, review, decide, change, report) can be run by whoever you name; the audit log and the decision records are the material for that report. Nothing in the AI can grant itself or anyone else a new power.",
    },
    {
        "key": "whatsapp",
        "title": "WhatsApp: should the assistant work between people, not only between a person and the map?",
        "ask": "Would you want Lumen to handle distributed coordination among humans navigating the territory, for example relaying 'is the pool open today?' to a steward and back, or posting a verified weekly digest to a group? Or should it stay a read-only guide inside the website for now?",
        "built": "Lumen is read-only and lives in the site. It answers only from verified records, shows where every answer came from, and can draft a suggestion for a steward when a signed-in person asks. No messaging channel is connected; the proposal's WhatsApp Business plan is logged as a separate, optional project with its own cost.",
        "changes": "Messaging means a third-party platform, a per-message cost outside the $500–$1,000 a year allowance, consent for every recipient, and a duplicate-aware ledger so nobody is messaged twice. It would need written approval before any build.",
    },
    {
        "key": "biodiversity",
        "title": "Biodiversity: what level of nature mapping do you want?",
        "ask": "Should the atlas name species and habitats (tide-pool life, redwood groves, the Smith River's runs), keep to places where families can see nature safely (beaches, trails, visitor centres), or leave biodiversity to the agencies and link out?",
        "built": "Trails, beaches, rivers and visitor centres are listed from official sources. Species and nesting or den sites are not mapped; the system has a 'sensitive' flag that keeps a place out of every fine-grained view and only ever shows it in coarse aggregates. The brief rules out exposing sensitive species sites.",
        "changes": "Species-level content would need a data-rights log for each source (iNaturalist, CDFW, the parks), a rule for which records are too sensitive to place at all, and a steward who knows the ground. Habitat-level notes on existing listings cost nothing and risk nothing.",
    },
    {
        "key": "nodes",
        "title": "Node adding: should the first 40 places be built by the people who have been here longest?",
        "ask": "Rather than Alex supplying 40 nodes, would it be better to ask Daniel, Sasha, you and others who have lived in Crescent City the longest to pilot the atlas and add the places they actually use? Alex has a few to add as well.",
        "built": "Fifty-eight places are live, each summarised from an official website and placed from an authoritative source (the state school directory, agency pages, or OpenStreetMap features in our own map tiles). Every one is labelled 'checked online, not visited'. None counts toward the forty until a person has confirmed it; the admin review queue orders that work by the value of each check.",
        "changes": "A pilot group with contributor rights can confirm, correct or reject each of the fifty-eight from their own knowledge, and add what is missing, inside the moderation workflow that already exists. That turns the online checks into the human-verified listings the brief asks for.",
    },
    {
        "key": "public",
        "title": "Public access and representation: how should a node be shown, given that a map is never complete?",
        "ask": "A map is a representational model, never the territory. How should the atlas say that? Should every place show its verification date and source as now, should unverified or disputed places appear at all, and how should we show the gaps (what we know we have not mapped)?",
        "built": "Every listing shows its source, how it was located, the date it was checked and a plain-language freshness band. Places that fail the recommendation test are shown with their status rather than hidden. The crescent logo is a gauge of the directory's own confidence. The footer and the home page say the map never claims to be a complete picture.",
        "changes": "We could add a 'what is not here yet' panel listing categories with few or no verified entries, and let stewards mark a place as 'disputed' or 'closed, kept for the record'. Public access itself remains your decision; the private preview can become public without code changes.",
    },
]
