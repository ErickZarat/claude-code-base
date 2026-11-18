---
name: router
description: Use when the user describes work in plain words without naming a command — picks the eng/OpenSpec/pstack/ponytail/graphify skill and where it runs (opus for plans).
---

# Router — plain message → the right skill, on the right model

Skip this skill when the user already named a command. Otherwise match the message to ONE row below, tell the user
in one line where it goes — `→ /eng:task (main session)` — and do it. Ambiguous between rows → ask one short question
with the 2–3 candidate rows; never guess.

## Routes
| The user wants… (any language, any wording) | Target | Runs in |
|---|---|---|
| a new feature / change / "let's build X" | `/opsx:propose` — via the `planner` agent, `mode: proposal`, **model opus**; then `/eng:spec` on its output | planner subagent (opus) |
| to check or tighten a proposal / specs | `/eng:spec` | main session |
| tickets on GitHub for a change | `/eng:epic` — **confirm first** (creates issues) | main session |
| to work on the next / a given ticket | `/eng:task next` or `/eng:task <#>` (its plan step runs the `planner` on opus) | main session |
| to fix a bug | `/eng:task new "<title>" --bug`; hard to reproduce → `/pstack:poteto-mode` | main session |
| to know if a change is done | `/eng:dod` | main session |
| a review of a PR / branch | `/eng:review [PR#]` — **confirm first** (runs reviewer agents) | main + reviewer agents |
| one review pass without the loop | `/eng:review-once [PR#]` — **confirm first** | main + reviewer agents |
| who is doing what / what's blocked | `/eng:status` | subagent, model haiku |
| to understand code: how, why, where | `graphify query "<question>"`, `/pstack:how`, `/pstack:why` | subagent, model haiku |
| less code / "is this over-engineered" | `/ponytail-review` (diff) or `/ponytail-audit` (repo) | main session |
| an architecture decision recorded | `decision` skill — on opus, **ask first** | main session |
| a plan without OpenSpec | `plan-change` skill — via the `planner` agent, `mode: task-plan`, **model opus** | planner subagent (opus) |
| lessons from past reviews | `/eng:retro` | main session |
| set up / update the standards in this repo | `/eng:setup` (`/eng:bootstrap` for CLAUDE.md only) | main session |

## How to dispatch
- **Manual-only eng skills** can't be invoked by the model: read `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` and
  follow it, with the user's words as its arguments.
- **Subagent rows:** launch the agent with the model in the table (Agent tool `model` parameter) and give it the
  user's request verbatim plus what it needs (change name, PR number). Bring back its short result; don't paste
  long output into the conversation.
- **Plans and proposals always go to the `planner` on opus** — no need to ask. **Ask before any other opus use**
  ("This looks like a design decision — use Opus? It costs more.").
- Session on opus and the route is ordinary implementation → suggest `/model sonnet` once.

## Never
- Merge, push to the default branch, close issues or delete anything because of a routed request.
- Chain several routes on your own: after one route finishes, suggest the next one and wait.
