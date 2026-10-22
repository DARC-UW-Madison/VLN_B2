# Contributing

[日本語](CONTRIBUTING.ja.md)

## Working agreement

- Read the README, project status, and the relevant guide before changing files.
- Keep each change focused. Explain the problem, the result, and its evidence.
- Distinguish proposed behavior, implemented behavior, and measured results.
- Keep private records, machine addresses, credentials, and unpublished lab
  materials outside this repository. Do not add personal labels, chat exports,
  or assistant-specific instruction files.

## Git and review

Use `main` for reviewed work. Start a short-lived branch such as
`docs/experiment-guide`, `feat/observation-reader`, `fix/timestamp-alignment`, or
`refactor/state-buffer`. These are examples, not existing implementations.

```sh
git switch main
# After a shared remote exists, update with: git pull --ff-only
git switch -c docs/experiment-guide
# Edit the relevant English and Japanese documents.
git diff --check
git diff
git add docs/development.md docs/development.ja.md
git diff --cached
git commit -m "Clarify experiment prerequisites"
```

Use a short imperative commit subject in English. Explain non-obvious reasons in
the body. Stage specific files; do not rewrite shared history. Use your own Git
identity and a GitHub noreply email when publishing.

Once hosted, open a pull request to `main` with the purpose, changes, checks and
remaining limitations. A team reviewer should review it before merge. Branch
protection and CI are not configured yet; this is the intended workflow, not a
claim that GitHub enforces it. Use version tags for releases, not copied folders.

## Documentation

English files use `.md`; Japanese counterparts use `.ja.md` in the same folder.
Link the two versions. Japanese prose uses `，` and `．`. Code, identifiers,
comments, command output, commit subjects, and pull requests use English.
Update both document versions in the same change; neither may omit caveats.

Keep this file brief. Put explanations in `docs/`: purpose, prerequisites,
terms, mechanism, steps, expected observations, failure cases, and limitations.
Use relative links, portable commands, SI units, and defined symbols. Cite
primary sources. Do not present unrun commands or a paper's results as local
validation. Record significant design decisions with reasons and alternatives
in the relevant guide; create a separate decision record only when needed.

## AI and parallel work

AI assistance follows the same review and evidence requirements as human work.
The contributor verifies generated code, citations, translations, and claims.
Do not upload private recordings, credentials, or unpublished research to an
external AI service without the laboratory's authorization.

Split substantial independent tasks into separate chats or agents when useful.
Give each a bounded task, owned files, base commit, and acceptance criteria.
Use separate branches or worktrees for concurrent edits; avoid two workers
editing the same files. One integrator reviews the combined result.
Hand off the commit, changed files, checks, limitations, and next step. Preserve
shared conclusions in `docs/status.md` and its translation, not chat transcripts
or personal task logs. A new session reads those documents rather than relying
on the original conversation.

## Before accepting a change

- Check both translations, relative links, commands, and `git diff --check`.
- Run checks relevant to the changed behavior and record their actual outcomes.
  Documentation review does not verify inference or robot operation.
- For experiments, record revisions, configuration, method, failures, and
  evidence as described in the development guide.
- Update project status when a milestone or next step changes.
- Before publication, confirm rights and third-party terms and inspect files
  and Git history for secrets or private data. Use `gitleaks git --redact .`
  when Gitleaks is available. Automated scanning does not replace human review.
