## Two Phases: Planning → Pipeline

This project uses two distinct phases. Never mix them.

### Phase 1: Planning (User + Claude)

Collaborative discussion — no agents, no pipeline. This is where we:
- Discuss features, priorities, and scope
- Enter plan mode for non-trivial tasks (3+ steps or architectural decisions)
- Write detailed specs upfront to reduce ambiguity
- Write plan to `tasks/todo.md` with checkable items
- If something goes sideways, STOP and re-plan — don't keep pushing

**When the plan is complete**, always ask the user explicitly:
> "Plan is ready. Start the pipeline? (PM → full agent pipeline)"

Do NOT start the pipeline without explicit user confirmation ("yes", "go", "build it").

### Phase 2: Pipeline Execution

Once the user confirms, run the orchestrator loop:

**Step 1 — Start the orchestrator:**
```
Agent tool:
  subagent_type: "orchestrator"
  prompt: "New pipeline. Feature: <description from planning>. Plan reference: tasks/todo.md. Determine pipeline variant (full or fix) and return first spawn instruction."
```
Save the returned `agent_id` — you will resume this same agent for the entire pipeline.

**Step 2 — Spawn the agent the orchestrator requested:**
Read the orchestrator's JSON response. It contains `next_agent` and `task_assignment`. Spawn that agent:
```
Agent tool:
  subagent_type: <next_agent from orchestrator response>
  prompt: <task_assignment from orchestrator response>
```

**Step 3 — Resume the orchestrator with the result:**
```
Agent tool:
  resume: <orchestrator agent_id from Step 1>
  prompt: "<agent> completed. Result at results/<result_file>.json"
```

**Step 4 — Repeat Steps 2-3** until the orchestrator returns `"next_action": "pipeline_complete"`.

**If orchestrator returns `"next_action": "pipeline_pause"`**: Stop and show the user the `reason` and `resume_instructions`. Wait for user input before resuming.

Never do routing yourself. Never read result `status` fields to decide next steps. Always ask the orchestrator.

---

## Workflow Standards

### Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- One task per subagent for focused execution

### Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Review lessons at session start for relevant project

### Verification Before Done
- Never mark a task complete without proving it works
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- Skip this for simple, obvious fixes — don't over-engineer

### Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user

---

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

---

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
