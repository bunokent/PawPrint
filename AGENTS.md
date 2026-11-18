# AGENTS.md — PawPrint

This project is governed by two skills. Read and follow both before writing any code:

1. **`.opencode/skills/pawprint/SKILL.md`** — PawPrint engineering & design conventions
   (2-mode access model, selector/service layering, axios client, YOLO-World gatekeeper,
   commit + tests + docs discipline).
2. **The `taste` skill** at `.agents/skills/design-taste-frontend/SKILL.md`
   (`design-taste-frontend`, tasteskill 2.5.1) — every UI component, page, form, modal and
   A4 flyer template must obey its visual and UX standards (one system, editorial type,
   equal edges, real photographs, hover micro-interactions, no violet, accessible contrast).

Every code change MUST ship with tests, an updated `docs/DOCUMENTATION.md` (12 sections,
including the living Tutorial log), a regenerated `docs/documentation.pdf`
(`npm run docs:pdf`), and a clean, atomic Conventional Commit.
