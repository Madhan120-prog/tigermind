# Git Workflow

## Branching
- One branch per `PLAN.md` phase: `phase-0-domain-recon`,
  `phase-1-housing-slice`, `phase-2-tier1-domains`, `phase-3-majors`,
  `phase-4-router-synth-guardrails`, `phase-5-eval-ci`, `phase-6-sis`.
- No direct commits to `main`. Branch → commit → PR → merge.

## Commits
- Conventional commit style: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- **Never add an AI co-author trailer to any commit in this repo.** The
  user is the sole author of record — Claude Code may run the git
  commands, but commit messages must not include `Co-Authored-By: Claude`
  or any equivalent. This overrides the default Claude Code commit
  template for this project specifically.

## PRs / merge
- Open a PR per phase branch. The user is the sole collaborator on this
  repo and performs every merge themselves — Claude Code opens the PR and
  stops there, never runs `gh pr merge` or merges via the GitHub UI.
- Self-review the diff before merging.
- A phase's eval subset (`eval/eval_set.csv`) must pass before merge — once
  Phase 5 CI is wired up (`PLAN.md` Section 9), this is enforced by GitHub
  Actions rather than manual discipline.
- **Merge with a regular merge commit — never squash, never delete the
  branch afterward.** The user wants every phase branch to stay visible in
  the repo permanently, so the phase-by-phase build history is browsable
  on GitHub rather than collapsed into `main`. Tag if the phase is a
  milestone (e.g. `v0.1` at the end of Phase 5's portfolio-ready
  checkpoint).
- `/clear` the Claude Code session after merging, before starting the next
  phase — each phase should start from a clean context, not one carrying
  forward the previous phase's exploratory reasoning.
