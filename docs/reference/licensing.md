# Licensing original work and upstream research software

[日本語](licensing.ja.md) · [Documentation](../README.md) · [Third-party inventory](../../THIRD_PARTY.md)

> Document type: **Reference**.

This guide explains the scope of the existing MIT license and how to decide what
can be published. It does not change the license or authorize a release. The
source repository, model files, datasets, container images and research results
are separate artifacts; one license label cannot establish rights to all of them.

## Why this repository can have a different license

A license is permission from a rights holder to use material they control. The
[MIT License](https://opensource.org/license/mit) gives broad permissions subject
to retaining its copyright and permission notices. Our [LICENSE](../../LICENSE)
applies to this project's independently authored code and documentation. It
cannot grant rights belonging to the TIC-VLA authors or another dependency.

For example, an original program that reads our own recorded observations,
calls an installed model's documented interface and saves our own measurements
does not become that model's implementation merely because it uses the model.
Conversely, copying an upstream inference function into our package and changing
its names does not make the copied material ours to relicense. The provenance
and relationship of each actual contribution matter.

Using a different license from an upstream project is therefore not by itself an
error. However, dependency separation is not a blanket legal determination that
every adapter or combined system is independent, or that a particular upstream
license permits every use. Inspect the actual material and applicable terms.

## What the TIC-VLA terms require us to distinguish

The inspected [TIC-VLA Academic Software License at revision
`9fa6f8b`](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md)
allows specified educational or academic research use by academic or nonprofit
researchers. It also prohibits onward transfer of the software, including
derivatives. It is not MIT and is not a general redistribution permission.

Keep these two questions separate:

1. May the intended researcher obtain and use the upstream artifact for the
   proposed purpose under its actual terms?
2. May this particular source file, modification, model or combined image be
   transferred to the intended recipient or published?

A permitted research use does not automatically answer the transfer question.
Do not assume another laboratory member is an authorized recipient just because
both people belong to the same organization. Ask the upstream rights holder or
the laboratory's appropriate research/licensing contact when the intended use,
recipient or derived artifact is not covered clearly. No such extra permission
is asserted by this repository.

Keeping restricted source outside Git helps prevent accidental publication.
It does not itself supply permission to obtain, use, modify or share it. A private
repository, SSH transfer, shared SSD, email attachment or Docker image can still
transfer restricted material. Renaming, translating, manually retyping or asking
an AI to rewrite upstream code does not establish independent ownership.

## Concrete examples for this project

| Proposed artifact or action | What to review |
|---|---|
| Independently authored inventory CLI, synthetic tests and explanatory manual | Confirm authorship and authority to release; original material can use this repository's MIT license |
| Original adapter calling a separately installed public API | Inspect its source provenance and the upstream use terms; an API call alone is not permission to redistribute the dependency |
| Upstream function copied or adapted into our source | Identify copied material and derivative terms; do not place it under our MIT notice or publish without applicable permission |
| Local patched upstream package | Retain its original terms and provenance; local research permission does not establish permission to share the patch or combined package |
| Docker image containing upstream source, model files or SDK binaries | Review every included component, recipient, notice and redistribution condition before transferring the image |
| Dockerfile containing our own installation recipe | Review the recipe itself and any downloaded components separately; permission to publish a recipe does not permit publishing its resulting image |
| Method described in a paper and implemented independently | Cite the paper, distinguish the method from copied implementation, and check relevant research agreements or other rights before release |
| Recorded camera stream, map or experiment log | Check privacy, laboratory authorization, dataset terms and unpublished results; repository MIT does not authorize disclosure |

These are review categories, not categorical rulings that an uninspected work is
or is not a derivative. A file-by-file and artifact-by-artifact provenance record
is more useful than changing the top-level license label.

## Should we invent a new custom license?

The current recommendation is to retain MIT for independently authored code and
documentation while preserving the separate upstream restrictions. Drafting a
new research-only license does not obtain rights from the upstream authors,
make restricted derivatives publishable or resolve a contributor's ownership.
It would instead introduce another set of conditions for collaborators to review.

Choose a different license for future original work only when the rights holders
and laboratory have an actual requirement, such as a sponsor's agreement or a
deliberate policy for distribution. Establish the intended permissions first,
then have the appropriate institutional contact review that choice. Do not copy
the TIC-VLA license and substitute our laboratory's name: we do not own its
material, and its transfer restrictions may not match our intended collaboration.

MIT also permits uses beyond academic research for the original material it
covers. That is an actual permission, not merely a credit statement. If the lab
intends to restrict those uses for future original contributions, decide before
their release. A later license change does not retract permissions already
granted for previously released copies.

## Rights holders and laboratory authority

The existing collective copyright notice identifies contributors without
assigning ownership to a university, laboratory or individual. Each contributor
must have authority to submit their material under the selected license.
Permission to create or push to a laboratory GitHub repository establishes
repository access; it does not establish copyright ownership or approval to
disclose every research result.

[UW-Madison's guidance on copyright and intellectual
property](https://rsp.wisc.edu/contracts/terms.cfm) describes its general approach
to researchers' copyright while also identifying sponsor-related obligations.
Check the actual appointment, funding and collaboration agreements rather than
inferring ownership from a university email address or GitHub organization.

## Weights, conversions and future independent research

Model architecture code describes a computation. Weights contain learned
parameters. A checkpoint may also contain optimizer state, metadata and other
serialized objects. Their terms may differ from one another and from a dataset
hosting page's license badge. Inspect the exact files, model card, source
revision and applicable conditions before acquisition or use.

Fine-tuning, quantization, format conversion or packaging does not by itself
remove conditions applying to the source weights or software. Do not label
derived weights MIT merely because the conversion script is MIT. New code,
learned weights, evaluation recordings and a paper are separate release decisions.

Future research can publish independently authored tools and descriptions while
documenting restricted external requirements. Reproducibility records can name
the upstream revision, acquisition method and configuration without bundling the
restricted files. Decide what recipients may acquire themselves under their own
applicable permissions; do not treat this as an authorized workaround for a
prohibited transfer.

## Contribution and release procedure

For each proposed contribution, record the author/source, exact revision where
relevant, original or adapted status, applicable terms and intended use. Put
public dependency information in [THIRD_PARTY](../../THIRD_PARTY.md); keep private
permissions and research agreements in approved laboratory storage.

Before the first public source push or a later artifact release:

1. Inspect the actual files and Git history for copied/restricted material,
   credentials, personal information and unpublished results.
2. Confirm that contributors may release their original material under the
   repository's license and that applicable lab/sponsor review is complete.
3. Inventory what the release includes: source alone, binaries, image layers,
   model files, datasets or recordings. Do not reuse a source-only review for an
   image or dataset release.
4. Resolve applicable permissions and required notices for those exact artifacts
   and recipients. Unresolved material stays out of that release.
5. Record the reviewed revisions, terms and release decision. Obtain the user's
   publication instruction before pushing. The initial source release to the
   lab repository has been made; repeat this procedure for each later artifact
   release.

The current repository keeps upstream code and weights outside public source.
The MIT scope remains original code and documentation. No new custom license,
upstream relicensing or permission to redistribute restricted artifacts is
introduced by this guide.
