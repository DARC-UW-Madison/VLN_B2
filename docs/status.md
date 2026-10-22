# Project status

[日本語](status.ja.md) · [Home](../README.md)

## Current stage

Repository preparation. The project is local; no GitHub remote, publication
license, or laboratory affiliation has been assigned. There are no B2 measurements.

| Deliverable | State | Evidence or completion condition |
| --- | --- | --- |
| Shared documentation and development rules | Prepared | README, Contributing, architecture, development guide, and third-party review |
| Hardware and software specification | Not started | Actual B2, compute, camera, state interface, and firmware are identified |
| Upstream permissions and dependency revisions | Open | Research use and sharing conditions resolved; exact revisions recorded |
| Offline inference | Not started | Reproducible prediction and failure-handling report |
| Live observation without commands | Not started | Time/frame alignment and command rejection demonstrated |
| Command interface and stop behavior | Not started | Reviewed test results from the actual robot |
| B2 navigation evaluation | Not started | Predefined tasks, complete trial counts, results and limitations |

## Decisions in effect

- Use the existing B2 walking controller; investigate a high-level navigation adapter.
- Keep proposed behavior separate from verified implementation and experiment results.
- Maintain English and Japanese documentation, with English code and configuration.
- Keep public-facing files free of personal labels, assistant instruction files,
  chat transcripts, machine addresses, and private research data.
- Keep upstream software and weights outside this repository. Do not assume that
  code, weights, and datasets share one license.
- Do not publish until the rights holder and project license are decided.

## Next deliverable

Prepare the environment specification described in [the development guide](development.md).
It must establish the available GPU/OS, camera input, timestamped robot state,
SDK/firmware compatibility, and operator stop procedure. Then choose an inference
environment and define an offline validation task. Do not invent hardware values
to make an installation guide appear complete.

## Continuing the work

A new task starts by reading this page, the relevant guide, and the current Git
diff. Use a branch for a bounded deliverable. On completion, update this page
and its Japanese counterpart with evidence, unresolved questions, and the next
action. Keep detailed experiment methods and results in reviewed reports rather
than expanding this page into a session log.
