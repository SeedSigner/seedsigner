# SeedSigner localization automation

Automates the source-string half of the localization workflow: keeping
`l10n/messages.pot` in sync with the code and getting it to Transifex without
manual coordination. On a PR it posts an advisory comment showing the
source-string changes; after merge it proposes the regenerated catalog as a
rolling PR and mirrors it to the translations repo's Transifex source.

This covers the `messages.pot` (source-string) stream only. Screenshot review
and `.po` round-trip are separate streams.

## Pieces

| File | Role |
| --- | --- |
| `schema/review-manifest.schema.json` | Contract for the data passed from the untrusted diff job to the trusted comment job. |
| `pot_diff.py` | Translator-meaningful diff between two catalogs (keyed on msgctxt + msgid; a plural-form change is reported as a change); builds the review manifest. |
| `render_comment.py` | Renders the advisory comment from a validated manifest (untrusted text is contained in a code fence). |
| `validate_manifest.py` | Validates a manifest against the schema and trust anchors before the trusted job acts on it. |
| `pot_sync_helper.py` | Decides whether a regeneration is a meaningful source-string change (ignores header and location churn). |

| Workflow | Trigger | Role |
| --- | --- | --- |
| `l10n-pot-diff.yml` | `pull_request` | Read-only, no secrets: extracts the catalog from the base and PR-head source, diffs them, uploads a manifest artifact. |
| `l10n-pot-comment.yml` | `workflow_run` | Trusted: validates the manifest and maintains one advisory comment. |
| `l10n-pot-sync.yml` | `push` to the default branch | Regenerates, opens/updates a rolling PR from a bot fork, mirrors to the translations bot fork. Operator setup: `SETUP.md`. |

## Trust model

Regenerating `messages.pot` runs the PR's own `setup.py` and source, which is
untrusted on fork PRs. So the advisory is split into a read-only producer and a
trusted consumer:

- `l10n-pot-diff.yml` runs in the PR context with no secrets and a read-only
  token; malicious PR code can do nothing but produce a manifest artifact.
- `l10n-pot-comment.yml` runs from default-branch code, never executes PR code,
  and treats the manifest as untrusted: it validates against the schema, checks
  the `repository` and `pr.head_sha` trust anchors, binds the PR number to the
  head SHA before commenting, and re-renders from validated fields.

The schema validates the manifest's shape, not its honesty: a malicious PR can
emit a schema-valid manifest, so it buys bounded, well-formed input for the
trusted job (size caps, required fields, no extra fields), not trust. Trust
comes from the anchors above, which are compared against values GitHub sets
authoritatively. The worst a valid-but-dishonest manifest can do is show
misleading source-string info on its own PR's advisory comment, which never
blocks the PR.

The post-merge sync writes only inside bot forks (never upstream) using
short-lived, least-privilege GitHub App tokens; see `SETUP.md`.

## Running the tests

These tests live outside the project's configured `testpaths` (`["tests"]`), so
the main suite does not pick them up. Run them explicitly:

```bash
python -m pip install -r l10n/requirements-l10n.txt   # Babel (message extraction)
python -m pip install jsonschema                       # for validate_manifest.py
python -m pytest l10n/automation/tests -q
```

## Local dry-run of the advisory diff

Diff the catalog extracted from your working tree against `HEAD` (the impact of
your uncommitted changes):

```bash
python setup.py extract_messages -o /tmp/head.pot
git stash --include-untracked
python setup.py extract_messages -o /tmp/base.pot
git stash pop
python l10n/automation/pot_diff.py \
  --base /tmp/base.pot --head /tmp/head.pot \
  --repository SeedSigner/seedsigner --pr-number 0 \
  --head-sha "$(git rev-parse HEAD)" --base-ref HEAD --out /tmp/manifest.json
python l10n/automation/render_comment.py --manifest /tmp/manifest.json
```
