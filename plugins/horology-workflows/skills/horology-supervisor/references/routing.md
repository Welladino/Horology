# Routing

## Choosing specialists

Choose from the installed specialist `horology-*` skills: research, technical assessment, security review, GTM, marketing strategy and content planner. Their names and descriptions say what each does; open a candidate's `SKILL.md` when the fit isn't clear. Ignore other installed skills. The Agent Register is an overview for the founder, not an input.

- Type chooses the route first. Feature, Enhancement, Refactor and Fix take the implementation route: the run writes its Stage 1 plan document (Plan template, or `horology-technical-assessment` when options must be compared first), implements the change itself, writes the Implementation report and proposes the Specialist deliverable decision; `horology-synthesis-artifacts` makes a page from the report only when the founder asks for one. Other specialists are used only for a step that asks for their kind of output (for example a security review of the change). Idea, Research, Direction and Plan take the investigation route below.
- On the investigation route, start from the question in Next step / Research question. Research and Idea questions usually go to research; a question about whether or how to build a change goes to technical assessment.
- Neighbouring specialists split the work like this:
  - **Security review** answers "is this safe, what are the risks"; **technical assessment** answers "should we build this change, and how".
  - **GTM** chooses who to sell to and the first channels; **marketing strategy** turns an agreed GTM direction into a plan; **content planner** plans and drafts the pieces. Without an agreed step before it, route to the earlier one.
  - **Research** answers a question; it doesn't choose positioning or write content.
- Several specialists on one item are fine when they answer different parts of the question. Run them side by side when neither needs the other's output; otherwise in order. Say why in Plan reason.
- If two fit equally, choose the narrower one and name the other in Plan reason.
- If the document graph already answers the question, write a short summary and propose a decision instead of new research.

## Checking results before review

- The bounded question is answered, or the gap that stops it is stated.
- Claims cite sources; code claims name the repository, branch and commit.
- Evidence, options, recommendation and uncertainty are kept apart.
- Nothing contradicts earlier decisions without saying so.
- `auto_link_similar_documents` scores of 0.90 or more are reported as near-duplicates.
- Outputs are in Drive, listed in the Document Index, and linked to the Pipeline ID.
- On the implementation route, the report names the branch, commits and pull request, the tests run, and each Steps row that was skipped or changed.
