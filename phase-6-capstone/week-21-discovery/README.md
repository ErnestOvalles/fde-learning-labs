# Week 21: Customer Discovery (Capstone)

## Outcome

Pick **one realistic AI product scenario** and produce the four artifacts that any FDE engagement starts with: a **synthetic customer persona**, a **discovery interview script**, a **requirements document** with measurable success metrics, and a **scope / non-scope statement**. By the end of the week you will have a single folder a real customer could read and say "yes, that is the problem I have" — without writing a single line of product code yet.

This is the most "soft" week of the path. The output is markdown, not Python. Treat it as seriously as the build weeks: vague discovery produces vague products.

## Setup Checklist

- [ ] A blank folder for your capstone scenario: `phase-6-capstone/week-21-discovery/scenario/`
- [ ] 60 minutes of uninterrupted thinking time
- [ ] A list of three real problems you have personally seen (from work, volunteering, side projects) — you will choose one
- [ ] Optional: a notebook for free-form sketching before you commit to markdown

### Setup Walkthrough

```bash
cd /tmp/fde-learning-labs/phase-6-capstone/week-21-discovery
mkdir -p scenario
cd scenario
touch 00-pitch.md
touch 01-persona.md
touch 02-discovery-script.md
touch 03-requirements.md
touch 04-scope.md
```

The five files map to the five micro-exercises below. Fill them in order; the later files depend on the earlier ones.

## Learning Path (60–90 minutes)

**Best approach:** Read **one** essay on customer discovery and **one** example requirements doc. Then start writing.

### Learn in this order

1. **What "discovery" means at an FDE shop** — not just "talk to customers" but the structure of the questions
2. **The Mom Test** — what you are not allowed to ask, why compliments lie, why hypotheticals lie harder
3. **Personas vs. jobs-to-be-done** — both are useful; personas describe who, jobs describe what they are trying to accomplish
4. **Success metrics that are not vanity** — leading vs. lagging indicators, what a number means in a business
5. **Scope as a contract** — what is in, what is out, what is "later", and what "later" means
6. **Risks and assumptions** — the list you write down so you do not get surprised
7. **What "AI" is actually doing in your product** — be honest about the parts that are rules, retrieval, generation, and which parts the user trusts

### Free Resources

- [The Mom Test (free summary)](https://momtestbook.com/) — rules for honest customer interviews
- [Continuous Discovery Habits (Teri Torres)](https://www.producttalk.org/product-management-resources/continuous-discovery-template/) — the underlying practice
- [Marty Cagan: Product vs. Feature Teams](https://www.svpg.com/product-vs-feature-teams/) — why discovery matters even on a small team
- [Ash Maurya: Running Lean](https://runninglean.co/) — the Lean Canvas, useful for one-page problem framing
- [Write the Docs: Documentation Principles](https://www.writethedocs.org/guide/writing/docs-principles/) — how to write a requirements doc that people actually read
- [OpenAI Cookbook: Evals](https://cookbook.openai.com/examples/evaluation/getting_started_with_openai_evals) — what "evaluation" looks like for an AI feature

**Tip:** Resist the urge to start designing the system this week. The point of Week 21 is to be sure you are solving the right problem. If you cannot write the success metrics, you are not ready to build.

## Micro-Exercises (45–60 minutes)

Complete these in order. Each builds on the last.

### Exercise 1 — Write a one-paragraph pitch for your scenario

*`scenario/00-pitch.md`*

```markdown
# Pitch

We help **[who]** do **[what]** so that **[measurable outcome]**.

Today they **[how they cope today]**, which costs them **[time, money, risk, frustration]**.

We will deliver **[what the product is, at a high level — not how]**.

We will know it works when **[one concrete number]**.
```

**Step-by-step:**
1. Pick a problem you have actually seen. Personal experience beats invention.
2. Fill in each bracket in one sentence. Do not edit; just fill.
3. The "we will know it works when" line is the seed of your success metrics in Exercise 4.
4. Examples:
   - "We help **small claims law firms** do **first-pass medical-records review** so that **the time-to-draft-summarize drops from 4 hours to 30 minutes**."
   - "We help **regional school districts** do **parent-communication drafting** so that **the principal's weekly writing time drops below 2 hours**."

### Exercise 2 — Write a synthetic customer persona

*`scenario/01-persona.md`*

```markdown
# Persona — Dr. Reyes

## Snapshot
- **Role:** Senior Manager, Operations Excellence, "Acme Health Plans" (a 400-employee regional health insurer)
- **Reports to:** VP of Operations
- **Team:** 7 direct reports (4 analysts, 3 ops engineers)
- **Location:** Hybrid — 2 days a week in the Phoenix office

## Day in the life
Dr. Reyes starts the day with a 30-minute standup, then blocks 90 minutes for email
and Slack. Most of the afternoon is in 30–60 minute meetings. After hours she
reviews the work her analysts produced that day.

## Current workflow
- Pulls 4 CSV exports from a vendor portal every Monday morning
- Asks an analyst to consolidate them into one master spreadsheet (≈ 3 hours)
- Reviews the spreadsheet, marks 6–10 items to follow up on
- Drafts a weekly executive summary in PowerPoint (≈ 2 hours)

## Pain points (in her words, paraphrased from the interview on 2026-04-12)
1. "The export formats change every quarter and I never know which column is the truth."
2. "My analysts are too good to be spending Monday mornings on copy-paste."
3. "By the time the deck is ready, the data is already a week old."

## Goals for the next 6 months
- Reduce weekly Monday-morning report time from 5 hours total to under 90 minutes
- Hand the analyst capacity back to higher-leverage work (e.g., root-cause analysis)
- Increase the freshness of the executive summary from 7 days old to 2 days old

## Tech comfort
- Comfortable in Excel and PowerPoint
- Has used ChatGPT at work with mixed results; skeptical of "AI features" but willing to try
- Will not use anything that requires IT to install

## Quote
> "I don't need a magic tool. I need the three hours of my Monday back."
```

**Step-by-step:**
1. One persona is enough for the capstone. Multiple personas are a sign you have not chosen.
2. The "in her words" line is the most important part — it is a quote, paraphrased, from a real conversation you had (or, in this synthetic exercise, that you can plausibly imagine).
3. The "tech comfort" line prevents you from accidentally building a CLI for a non-technical user.

### Exercise 3 — Write a discovery interview script

*`scenario/02-discovery-script.md`*

```markdown
# Discovery interview script

**Goal of this interview:** Understand how Dr. Reyes and her team currently
spend Monday morning, what they have already tried, and what would have to
be true for them to adopt a new tool.

**Length:** 30 minutes. No demos, no slides.

## Opening (3 min)
- Thank them for the time.
- Restate the goal in one sentence: "We are trying to understand what your
  week looks like. There are no right answers."
- Ask: "Is it still a good time for 30 minutes?"

## Context (5 min)
- "Walk me through last Monday, hour by hour. What did you start with, what
  did you finish with, what was in between?"
- "Where did the inputs come from?"
- "Who else touched the work?"

## Current behavior (10 min)
- "What is the most tedious part of that process?"
- "What have you already tried to make that easier?" (already-tried answers
  are the most honest data)
- "What did you try that did not work, and why?"

## Success criteria (7 min)
- "If a magic tool existed, what is the first thing it would do for you on
  Monday morning?"
- "If we did that, what would change about the rest of your week?"
- "How would you measure that change?"

## Risks and edge cases (3 min)
- "What would have to be true for you to trust the output?"
- "If the tool got it wrong, how would you find out?"

## Close (2 min)
- "Is there anyone else I should talk to?"
- "May I follow up by email if I have a small question?"

## After the call
Within 24 hours, write a one-paragraph summary in `notes/<date>-<name>.md` with:
- Top three pain points in their words
- The one number they would care about
- The one thing that surprised you
```

**Step-by-step:**
1. The script is not a survey. The questions are open-ended; you are listening for **what they volunteered**, not what they agreed with.
2. The "what have you already tried" question is the one that always reveals the truth.
3. Keep the script under 1 page. A long script is a sign you do not yet know what you are looking for.

### Exercise 4 — Write the requirements document

*`scenario/03-requirements.md`*

```markdown
# Requirements — Acme Monday Report

## Problem
The Operations Excellence team at Acme Health Plans spends 5 hours every
Monday producing a weekly executive summary from four vendor CSV exports.
The output is one PowerPoint deck for the VP, distributed on Wednesday.

## Users
- **Primary:** Dr. Reyes (Senior Manager, Operations Excellence) — reviews and signs off
- **Secondary:** 4 analysts — currently produce the work; will become reviewers
- **Tertiary:** VP of Operations — final consumer, never logs in

## Functional requirements
- **F1.** The system ingests the four CSV exports the team currently downloads.
- **F2.** The system produces a draft PowerPoint with the same 6 sections
  the current deck has, populated from the new data.
- **F3.** The system flags any cell that exceeds a 10% week-over-week change
  for human review.
- **F4.** A human reviewer can edit any cell, and the edits are recorded
  in an audit log.
- **F5.** The export is a downloadable .pptx file.

## Non-functional requirements
- **N1.** End-to-end Monday-morning time: under 90 minutes.
- **N2.** p95 latency for a single export: under 5 minutes.
- **N3.** Available Monday 06:00–12:00 local time, ≥ 99% over a 30-day window.
- **N4.** All data is processed in a tenant-isolated environment.
- **N5.** No customer PII is sent to a third-party LLM provider; only
  aggregated counts and pre-redacted snippets cross that boundary.

## Success metrics
- **Primary:** Monday-morning report time, measured by self-report, drops
  from 5 hours to under 90 minutes within 4 weeks of pilot.
- **Secondary:** Number of analyst-hours reallocated to root-cause work
  per week, target ≥ 8 hours.
- **Counter-metric:** Number of report errors that reach the VP. Target: 0
  errors of the "wrong number" class. Other classes are tracked but not blocked.

## Out of scope
- Real-time data ingestion (Monday-morning batch is the contract).
- Editing the underlying source data.
- Any of the 4 vendor formats being changed by us.
- Multi-tenant SSO (single-tenant pilot only).

## Risks and assumptions
- **A1.** The four CSV export formats are stable enough to parse without
  per-quarter schema work. *Validate by inspecting 8 weeks of exports.*
- **A2.** The team will accept a draft that still needs human review.
  *Validate in the first pilot week.*
- **A3.** The PowerPoint template can be reproduced from the data we have.
  *Validate by reproducing last week's deck exactly.*
- **R1.** Hallucination risk: a number is invented. *Mitigation: every
  cell is grounded in a row of the source CSV; the system cites the
  source row id.*
- **R2.** Cost overrun on the LLM side. *Mitigation: cache common summaries;
  the model's "thinking" cost is bounded by the number of cells.*

## Open questions
- Is there a way to get the CSV exports via API instead of manual download?
- Is there a sandbox version of the vendor portal we can hit from CI?
```

**Step-by-step:**
1. Every functional requirement should be testable: "I can click this button and see this output."
2. Every non-functional requirement should have a number. "Fast" is not a requirement.
3. The **counter-metric** is the one that prevents you from shipping something harmful while chasing the primary metric.
4. Risks and assumptions are the same document — write them now, not the week before launch.

### Exercise 5 — Write the scope / non-scope statement

*`scenario/04-scope.md`*

```markdown
# Scope — Acme Monday Report pilot

## In scope
- 1 customer (Acme Health Plans)
- 1 user role (Operations Excellence team)
- 4 source CSV exports
- 1 output format (.pptx)
- 1 business day per week of use (Monday)
- 4-week pilot

## Out of scope (during pilot)
- Other customers, even if requested
- Other source data, even if requested
- Other output formats (PDF, Google Slides, etc.)
- Real-time alerts
- Mobile or tablet views
- On-prem deployment
- Tenant-branded UI (we use a neutral UI for the pilot)

## "Later" — not in pilot, possibly in v2
- Multi-customer
- Source-API ingestion
- PDF and Google Slides output
- Multi-language summaries
- Self-serve onboarding

## What "later" means
A feature is "later" if it would be useful in a second contract with the
same customer, and **only** in a second contract. Features that would be
useful to a different customer are out of scope for this product.
```

**Step-by-step:**
1. The "later" section is the most important one. Without it, every future ask becomes a "small extension" that breaks the schedule.
2. "What 'later' means" is the rule that protects you. Write it before you need it.
3. The out-of-scope list is the document you point at when a stakeholder asks for something. Saying "no" is much easier when the list is already written.

---

## Main Lab: Pick a Scenario and Build the Four Artifacts (4–5 hours)

### Scenario

You are a forward-deployed engineer starting a new engagement. You have been given a 30-minute kickoff with a synthetic customer and a one-line ask from your team lead. You have one week to come back with: a real understanding of the customer, a written-down problem, a measurable definition of success, and a scope that protects the schedule.

### Build Steps

**Commit after each step.** The four artifacts are the deliverables; commit them in order.

#### Step 1 — Choose a problem you have actually seen

*`docs: choose capstone scenario`*

Open `scenario/00-pitch.md` and fill the template. The four constraints:

1. You have personally seen the pain point happen (not just read about it).
2. The work has a **measurable** cost today (hours per week, dollars per quarter, errors per month).
3. A reasonable person would say "yes, an AI can help" without it being hand-wavy.
4. The work involves a human reviewing AI output (not fully autonomous).

If you cannot find a problem that meets all four, choose a different problem.

#### Step 2 — Write the persona and the interview script

*`docs: write persona and discovery script`*

Copy the templates from Exercises 2 and 3 into `scenario/01-persona.md` and `scenario/02-discovery-script.md`. Fill them in. Important rules:

- The persona must have a **name**, a **role**, and a **quote**. If your persona has no quote, you do not yet have a person — you have a wish.
- The interview script must contain at least one question about what they have **already tried** and at least one about what would have to be true for them to **trust** the output.
- If you cannot honestly answer the "what have they already tried" question, schedule a real or simulated interview and come back to this step.

#### Step 3 — Write the requirements document

*`docs: write requirements doc`*

Copy the template from Exercise 4 into `scenario/03-requirements.md`. Fill the four sections:

1. **Functional** — every requirement is testable in one sentence.
2. **Non-functional** — every requirement has a number.
3. **Success metrics** — at least one primary, one secondary, one counter-metric.
4. **Risks and assumptions** — at least three of each, written as statements, not wishes.

Review the document with the lens: *could a different engineer, reading only this, build the right thing?* If not, the doc is not done.

#### Step 4 — Write the scope statement

*`docs: write scope statement`*

Copy the template from Exercise 5 into `scenario/04-scope.md`. Fill the four sections. The "later" list is what protects the schedule. The "what 'later' means" rule is the one that prevents the "later" list from growing without limit.

#### Step 5 — Run a discovery dry run

*`docs: dry-run discovery interview`*

Either:

- Schedule a 30-minute call with the synthetic persona (a friend acting as Dr. Reyes), OR
- Write a 1-page `notes/dry-run.md` answering the discovery script's questions as if you were Dr. Reyes

The goal is to **discover** a fact you did not know when you wrote the persona. If the dry run confirms everything you already wrote, the scenario is too well-known to you and you should pick a different one.

#### Step 6 — Get a review

*`docs: incorporate review feedback`*

Hand the four files to one person who has not seen them — a friend, a coworker, a forum. Ask them to read the requirements doc and answer, in writing:

1. What problem is this solving?
2. How would you know it is working?
3. What is the smallest thing you would build first?

If their answers do not match yours, the doc needs another pass. Document the feedback and the changes you made in `scenario/05-review.md`.

#### Step 7 — Lock the scenario and announce it

*`docs: lock scenario`*

Create `scenario/README.md` that links the four files in order and includes a one-paragraph summary. Commit it. From this point on, the scenario is **frozen** — every later week's work is judged against the four artifacts you wrote this week.

### Required Manual Tests

- [ ] The pitch fits in 60 seconds when read aloud
- [ ] The persona has a name, role, and a quote
- [ ] The interview script has at least one "what have you already tried" question
- [ ] The requirements doc has at least 4 functional, 3 non-functional, and 1 counter-metric
- [ ] The scope statement has a "later" list and a "what 'later' means" rule
- [ ] At least one person outside your head has read the four files and given feedback
- [ ] The feedback is documented and the doc was updated in response

### Acceptance Criteria

- [ ] All five markdown files exist under `scenario/`
- [ ] Every functional requirement is testable in one sentence
- [ ] Every non-functional requirement has a number
- [ ] There is at least one counter-metric
- [ ] The persona has a quote and at least 3 distinct pain points
- [ ] The interview script is under 1 page
- [ ] The scope statement names a "later" list and a rule for what "later" means
- [ ] A 5-minute verbal summary of the scenario can be given without reading the docs
- [ ] At least 5 meaningful commits

## AI-Off Check (30 minutes)

**Without looking at your docs**, write a 3-bullet pitch for your scenario in plain text:

```text
- WHO:   <one specific role, named persona>
- WHAT:  <the work they do today, in 1 sentence>
- WIN:   <the number that moves, in 1 sentence>
```

If you cannot write the 3 bullets cold, the scenario is not yet internalised. Try again. Then compare with your `00-pitch.md`. The goal is to be able to describe the scenario in any room, in any format, without notes.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. What did the discovery dry run reveal that you did not know when you started?
2. Which success metric would you drop if you could keep only one? Why?
3. Which item in your "out of scope" list do you expect to be challenged on? How will you respond?
4. What assumption, if wrong, would invalidate the entire project?
5. If you had to defend this scenario in 5 minutes to a senior FDE, what is the one question you would expect?

## Next Steps

Once you pass all acceptance criteria:

1. Schedule a real or simulated 30-minute discovery interview and write `notes/`
2. Write the reflection answers
3. Commit with message: `docs: week 21 complete`
4. Move to Week 22 — you start building the product

---

**Ready?** Start by:

```bash
mkdir -p phase-6-capstone/week-21-discovery/scenario
cd phase-6-capstone/week-21-discovery/scenario
```

Open a blank `00-pitch.md` and write the four lines of the pitch. The rest follows. Good luck! 🎯
