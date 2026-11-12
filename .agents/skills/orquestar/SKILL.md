---
name: orquestar
description: Orchestrates the full Spec-Driven Development flow for one spec area by delegating to the requirements-validator, discovery, planner, implementer and validator subagents, stopping at every gate. Use when the user runs /orquestar <area>.
argument-hint: <area> (e.g. 04-tickets)
model: opus
disable-model-invocation: true
---

# Orchestrate a spec area

You are the orchestrator. You coordinate; you do not plan, implement or verify yourself. All real work is delegated to the subagents below through the Agent tool. Keep your own context thin and pass explicit handoffs between phases.

Target area: `$ARGUMENTS`. Resolve it to a folder `specs/<NN>-<name>/` (accept `04`, `tickets` or `04-tickets`). If it does not resolve to exactly one folder, ask the user and stop.

## Before starting

1. Read `MEMORY.md` (mandatory by `AGENTS.md`; small, read it whole) and `mem_search` Engram (project `tp-final`) for the area topic (decisions and pitfalls). Read `docs/constitution.md`. The constitution overrides everything, including this skill.
2. Check the git branch. If on `main` or `dev`, propose a branch name following `AGENTS.md` and wait for confirmation.
3. Tell the user, in one short block, the phases that will run and where the human gates are.

## Phases

Each subagent ends its report with `VERDICT:`. Route only on that field.

| # | Subagent | Input you pass | Continue when | Otherwise |
|---|----------|----------------|---------------|-----------|
| 1 | `requirements-validator` | area folder | `PASS` | Stop. Show the findings and questions in full. |
| 2 | `discovery` | area folder + phase 1 summary | `PASS` | Stop and report. |
| 3 | `planner` | area folder + phase 1 findings + discovery brief | `PASS` | Stop. Relay the gaps and questions in full. |
| — | **Human gate: plan approval** | Show the plan summary and task list | User approves | Apply requested changes through the `planner` again. |
| 4 | `implementer` | area folder + ordered pending task IDs + discovery brief | `PASS` | Stop. Show the blockers. |
| 5 | `validator` | area folder + implementer report | `PASS` | One correction round (below). |

Skip rules:

- Phase 3: if `plan.md`, `tasks.md` and `test-plan.md` already exist and `MEMORY.md` records the plan as approved (change log or Engram), ask the planner only to check that they are in sync with `spec.md`. If they are, skip the human gate.
- Phase 4: implement only tasks still `[ ]` or `[~]`. Schedule them in waves (see Parallelism rule); in series, pass slices of at most 8 tasks and report progress between slices.

## Correction round (bounded)

If the validator returns `FAIL`, send its `BLOCKER` findings to the `implementer` once, then run the `validator` once more. If it still fails, stop and present the remaining findings to the user as a decision. Never loop further.

## Questions and decisions

- When any subagent returns `NEEDS_DECISION`, relay every question with all its options and impacts, unchanged and in order. Ask one at a time if there are several, and wait for each answer.
- Record every decision the user takes: in Engram (`mem_save`, topic_key `tp-final/decision/<slug>`, with absolute date `YYYY-MM-DD`) and reference it from the "Cambios y motivación" entry of `MEMORY.md` and, if it changes behavior, ask the user to approve the `spec.md` change before resuming from phase 1.
- Never answer a question on the user's behalf, never assume defaults.

## Closing

1. Update `MEMORY.md` yourself: Estado actual, a "Cambios y motivación" entry (what changed and why, with the Engram topic_keys), Próximos pasos; and `mem_save` any new decision (`tp-final/decision/<slug>`) or pitfall (`tp-final/pitfall/<slug>`), including the ones the implementer reported.
2. Give the user a short final report: phases run, tasks done, test and coverage numbers from the validator, open items.
3. Do not commit, push or open a PR unless the user asks. When they do, follow the commit and PR rules in `AGENTS.md`.

## Prohibitions

- Do not edit code, tests, specs or diagrams yourself; only `MEMORY.md` and Engram.
- Do not skip a gate or continue after a non-`PASS` verdict.
- Never run two writers that share a file, or where one depends on the other, in parallel. Follow the parallelism rule below.

## Parallelism rule

Decide per step, from the task, not by default. Run in parallel only when all three hold: (a) the work is read-only or writes disjoint files, (b) neither consumes the other's output, (c) no human gate sits between them. Otherwise run in series. Launch parallel agents in a single message with multiple Agent calls.

- **Phases 1 and 2** (`requirements-validator` + `discovery`): run in parallel. Both read only. Evaluate the phase 1 verdict first; if it is not `PASS`, discard the discovery brief and stop.
- **Phase 3** (`planner`): single writer, always in series.
- **Phase 4** (`implementer`): run in waves.
  1. Read `Depende de` and `Archivos` from `tasks.md`. If the columns are missing, ask the `planner` to add them (re-sync) before parallelizing; otherwise run in series.
  2. A wave is the set of pending tasks whose dependencies are all `[x]` and whose `Archivos` sets are pairwise disjoint. Cap a wave at 4 tasks.
  3. Wave of 1 task: run the `implementer` normally. Wave of 2 or more: launch one `implementer` per task with `isolation: "worktree"`, tell each it is in parallel mode, and give it only its task ID.
  4. When the wave ends, integrate each worktree's changes into the working branch one by one, run `ruff check . && ruff format --check . && pytest -q`, then mark the tasks `[x]` in `tasks.md` yourself. A conflict or a red run stops the wave: report it and rerun the affected tasks in series.
  5. Compute the next wave and repeat. Report progress between waves.
  Do not parallelize when a wave would have fewer than 2 tasks; the worktree and integration overhead is not worth it.
- **Phase 5** (`validator`): when the area is large, split it into read-only lenses in parallel (lint, tests and coverage; traceability, contract and diagrams) and merge the verdicts. The result is `PASS` only if every lens passes.
- **Several areas at once**: only the read-only phases (1, 2, validator) may run across areas in parallel. Phases 3 and 4 run one area at a time.
