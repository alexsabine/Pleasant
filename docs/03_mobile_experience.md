# Mobile-first information architecture — visual look owned by project lead

## Main navigation
1. **Explore**: accessible searchable list with map toggle, not map-only.
2. **This week**: dates, recurring family events, expiry/freshness.
3. **For my family**: filters by age band, budget, access needs; explicit optional saved settings, not child profiles.
4. **Local help**: family services, vetted providers, contact details with source.
5. **About / feedback**: explanations of visibility, licences, who governs it and how to correct a listing.

## Onboarding
Public visitor sees no forced login or location permission. Ask no more than one voluntary question at a time. Offer 'Just show free things' and 'Show all' affordances. Allow detailed/compact cards. Family/resource guidance is not medical/legal/emergency advice.

## Example interactions (later read-only agent)
- 'Free rainy-day activities for a 9-year-old in Crescent City?' -> 2–4 verified suggestions with explicit currentness and an offer to broaden.
- 'Where can we go with a wheelchair?' -> do not assume UNKNOWN accessibility is accessible; show verified and unverified separately.
- 'What was corrected about this playground?' -> show authorised edit history, not private reports.
- 'Can I add a photo of the path?' -> draft, optional EXIF location hint + user confirmation, remove location EXIF from public derivative, moderator approves.

## Admin/editor experience
One dashboard: Resources | Events | Pending review | Locations | Users (admin only) | Feedback. Public contribution creates a draft with provenance. Publishing always writes a revision and invalidates derived map tiles/cache.

## Accessibility
WCAG 2.2 AA, keyboard interaction, form labels/errors, map alternative (list), alt text, sufficient contrast, reduced motion, meaningful touch target sizes, easy switch to text-only and calendar list.
