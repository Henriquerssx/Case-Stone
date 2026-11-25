# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Primary (confirmed 2026-11-24):** the Stone × Inteli Academy evaluation panel. They watch a live demo of the dashboard during an in-person pitch. They need to understand in seconds what was measured, what the top content has in common, and see the agent produce a script.
- **Secondary (inferred from the brief):** the Impulso Stone content team. After the case, they generate scripts and check niche benchmarks.

## Product Purpose
Map what the highest-engagement posts aimed at micro and small entrepreneurs (MPEs) have in common, using 6,675 Instagram and YouTube Shorts posts from 55 profiles. Turn those patterns into ready-to-record video scripts for @impulsostone. Every script is linked to the real posts it relies on. Success means evaluators trust the method and leave remembering the mechanism: real posts → patterns → script.

## Positioning
Every recommendation and every creative points back to real, verifiable posts (validated `post_id`s). Patterns are reported as observed, not causal. They are read two ways, per post and per creator, and stress-tested by a weighted index (niche, creator, period, account size).

## Operating Context
- Shown live on a laptop or projector during a pitch. Generation runs live by default; an offline toggle (precomputed answers) keeps the demo working without API quotas or internet.
- Runs locally: `streamlit run demo/app.py`. Fresh clones load the public sanitized base from `data/release/`.

## Capabilities and Constraints
- Streamlit app (Python). Charts use Plotly. No custom frontend build step.
- The public repo carries no third-party text: captions, covers and comment text exist only in a local base. The dashboard must still work without covers.
- Free-tier LLMs only. Live generation takes about 30 s and can fall back to a template.

## Brand Commitments
- Visual identity pinned by the user: an "extreme reference" to Clube dos Sonhos (clubedossonhos.org.br), plus Impulso Stone colors.
  - Ink `#03211D`, deep `#055046`, ink-soft `#06352E`, teal `#32ADA1`, mist `#E6EAE9`.
  - Impulso lime `#C7F93C` and Sherwood `#004132`.
  - Manrope and Outfit, the star motif.
- No Stone or Impulso logos (registered marks).
- No AI-tool attribution in the repo or commits.
- Voice: Portuguese (pt-BR), informal second person ("você"), as on both reference sites.

## Evidence on Hand
- Real data in `data/release/` and `outputs/`: patterns, lift, niches, IDP, agreement, playbook with 6 creatives.
- Post covers exist only in the local `data/media/thumbs/` (not public).
- Human validation of 50 posts is **pending**. A blind AI labeling exists and must be labelled as AI, never as human.

## Product Principles
1. Prove, don't claim: every number is traceable to data, every creative to posts.
2. Observed, not causal: the interface never promises results.
3. Demo never breaks: offline mode and graceful fallbacks.
4. Public by default: nothing in the interface depends on third-party text being present.

## Accessibility & Inclusion
WCAG AA contrast on the dark ground. Charts never rely on color alone: there are labels and tables. Body text is ≥ 14 px when projected.
