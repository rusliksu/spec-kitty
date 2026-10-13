---
title: How to implement a work package
description: 'How to implement a work package with Spec Kitty 3.2: Use this guide to implement a single work package (WP) in its execution workspace.'
doc_status: active
updated: '2026-06-14'
audience: docs/context/audience/external/project-owner.md
type: how-to
related:
- docs/guides/how-to/missions/generate-tasks.md
- docs/guides/how-to/missions/handle-dependencies.md
- docs/guides/how-to/missions/review-work-package.md
- docs/guides/how-to/collaboration/worktrees-with-mcp-agents.md
---
# How to implement a work package

Use this guide to implement a single work package (WP) in its execution workspace.

## Prerequisites

- Tasks have been generated and finalized
- You know the WP ID (for example, `WP01`)

## Step 1: Get the WP Prompt

Use the slash command in your agent (recommended):

```text
/spec-kitty.implement
```

Or run the workflow command directly:

```bash
spec-kitty agent action implement WP01 --agent <agent>
```

This moves the WP to `lane: "doing"` and prints the full prompt plus the completion command.

## Step 2: Create or Resolve the Workspace

The canonical way is via the agent loop (recommended):

```bash
spec-kitty next --agent <agent> --mission <slug>
```

Your agent will call `spec-kitty agent action implement WP01 --agent <name>` for each WP, which resolves the correct execution lane workspace automatically.

> **Advanced / internal tool**: `spec-kitty implement WP01` is available as a lower-level direct invocation for advanced users. Prefer `spec-kitty next` for the standard workflow.

If the WP depends on another WP, task finalization will already have assigned it to the correct execution lane. Both the agent loop and the direct invocation handle this automatically.

## Step 3: Work in the Resolved Worktree

### Use an existing owned checkout

For a single-branch mission already committed in a registered Git checkout,
pass the same explicit checkout to the loop and the action commands:

```bash
spec-kitty next --agent <agent> --mission <slug> --owned-checkout /path/to/checkout
spec-kitty agent mission record-analysis --mission <slug> --input-file analysis.md --owned-checkout /path/to/checkout
spec-kitty agent action implement WP01 --agent <agent> --mission <slug> --owned-checkout /path/to/checkout
```

The checkout must belong to the current repository, remain on the mission's
target branch, and contain its committed planning artifacts. Dependencies,
analysis freshness, branch protection, actor ownership, and review checks still
apply. This path reuses the checkout; it does not allocate a lane worktree or
refresh user-global commands and runtime assets.
Project schema and version-pin checks run against the declared checkout.

Keep `--owned-checkout` on the completion commands printed in the prompt:

```bash
spec-kitty agent tasks mark-status T001 --status done --mission <slug> --owned-checkout /path/to/checkout
spec-kitty agent tasks move-task WP01 --to for_review --auto-commit --mission <slug> --owned-checkout /path/to/checkout
spec-kitty agent action review WP01 --agent <reviewer> --mission <slug> --owned-checkout /path/to/checkout
```

Commit any remaining command-generated bookkeeping in this checkout before the
next claim. Dirty or staged planning files are refused rather than
included in a status commit. Review commands use the proven base and the
implementation HEAD captured before the review claim. If the branch or
implementation changes during that claim, rerun review without reverting the
concurrent changes.

In your terminal:

```bash
cd <path printed by spec-kitty agent action implement>
```

Implement the prompt, run required tests, and commit your changes in that workspace. Sequential WPs in the same lane reuse the same worktree, for example `.worktrees/###-feature-lane-a`.

## Step 4: Mark the WP Ready for Review

Use the exact command printed in the prompt. In your terminal:

```bash
spec-kitty agent tasks move-task WP01 --to for_review --note "Ready for review: <summary>"
```

## What Happens

- An execution workspace is created or reused for the WP (`.worktrees/###-feature-lane-a/`)
- The WP lane is updated to `doing`
- Dependencies are enforced through lane computation in `finalize_tasks`

> **Note**: Spec Kitty creates one git worktree per execution lane. If task finalization computes one lane, the feature uses one worktree.

## Troubleshooting

- **"lanes.json is required"**: Run task finalization before implementation.
- **"WP missing from lanes.json"**: Re-run task finalization so the WP is assigned to a lane.
- **No prompt shown**: Run `/spec-kitty.implement` or `spec-kitty agent action implement` again.

---

## Command Reference

- [Slash Commands](../../../api/slash-commands.md) - All `/spec-kitty.*` commands
- [Agent Subcommands](../../../api/agent-subcommands.md) - Workflow commands
- [CLI Commands](../../../api/cli-commands.md) - Full CLI reference

## See Also

- [Generate Tasks](generate-tasks.md) - Required before implementation
- [Keep MCP Agents in the Worktree](../collaboration/worktrees-with-mcp-agents.md) - Keep editor sessions attached to the active worktree
- [Handle Dependencies](handle-dependencies.md) - How dependencies shape execution lanes
- [Review a work package](review-work-package.md) - Next step after implementation

## Background

- [Execution Lanes](../../../architecture/execution-lanes.md) - How lane worktrees are computed and reused
- [Git Worktrees](../../../architecture/git-worktrees.md) - How worktrees work
- [Kanban Workflow](../../../architecture/kanban-workflow.md) - Lane transitions

## Getting Started

- [Your First Mission](../../tutorials/your-first-mission.md) - Complete workflow walkthrough
- [Multi-Agent Workflow](../../tutorials/multi-agent-workflow.md) - Parallel development
