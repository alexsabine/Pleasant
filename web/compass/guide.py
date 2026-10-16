"""Lumen guide mode: what Lumen can do, and the questions the team asks the reviewer
(Kim) about how the mapping and agentic system should work. Plain data rendered into the
panel; answers are stored as ReviewNote rows (hosted) or compiled to text (static preview)."""

INTRO = (
    "Hello. I am Lumen, the guide for Crescent Compass. I answer only from the verified directory: places by age, cost, access and community, "
    "and what is on this week. Every answer shows where it came from and when it was checked, and I say so when I do not know. "
    "Signed in, you can also say \"correct: ...\" or \"suggest: ...\" and I draft it for a steward; nothing publishes on its own.\n\n"
    "Kim, the team would like your view on how this should work. Press \"Help shape Lumen\" to answer a few short questions, "
    "or just ask me something about Del Norte County."
)

QUESTIONS = [
    {"key": "serve_first", "text": "Who should Lumen serve first: newcomers finding their feet, caregivers of young children, teenagers, local organisations, or someone else?"},
    {"key": "allowed_to_do", "text": "What should it be allowed to do? Only answer from verified records (as now); also draft suggestions and corrections for a steward (built, needs sign-in); or, later, act with explicit consent, such as sending a message or a reminder?"},
    {"key": "uncertainty", "text": "When a listing was checked months ago and I am not sure it is still right, should I stay quiet, show it with a clear warning (as now), or ask you before showing it?"},
    {"key": "memory", "text": "I keep no memory of conversations. Should I use a member's saved settings, such as age bands and budget, when they choose to save them (as now), or always start from scratch?"},
    {"key": "channels", "text": "Where should I live? Only inside the website; also as an email digest people opt into; or in WhatsApp or text messages, which would be a separate, approved project?"},
    {"key": "initiative", "text": "Should I ever speak first, for example a weekly \"what is on\" note to people who asked for it, or only ever answer when asked?"},
    {"key": "red_lines", "text": "What is the line I must never cross? Say what would make you stop trusting me."},
    {"key": "map_wishes", "text": "Last one: what should the map show, or do, that it does not today?"},
]

CLOSING = ("Thank you. I have passed your answers to the stewards; they are not published anywhere. "
           "You can ask me anything about the county now. I don't keep our conversation; each question is answered on its own.")
