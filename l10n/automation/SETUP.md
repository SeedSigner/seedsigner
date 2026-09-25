# l10n automation: operator setup

The advisory-comment workflows need no setup (they use the repository's own
`GITHUB_TOKEN`). The post-merge sync (`l10n-pot-sync.yml`) needs a bot account
and GitHub App credentials, configured through repository variables and secrets.

The sync job no-ops until `L10N_BOT_FORK` is set, so the workflow is safe to
merge before any of this exists.

## Topology

The sync never writes to an upstream repo. It pushes the rolling `messages.pot`
branch to a bot-owned fork and opens a PR from there:

- `<bot>/seedsigner`: fork of the main repo; source of the rolling messages.pot PR.
- `<bot>/seedsigner-translations`: fork of the translations repo; the Transifex
  source-mirror target.

The bot forks must be real GitHub forks (same fork network) so the cross-fork PR
is allowed, and their default branches should track upstream (otherwise the
rolling-branch push re-introduces `.github/workflows/` files and the Fork App
then also needs `workflows: write`).

## Credentials: GitHub App(s)

The bot authenticates as a GitHub App (no long-lived PATs); the workflow mints
short-lived, least-privilege installation tokens at runtime. Two logical roles:

- PR role: `pull-requests: write` on the main repo; opens the rolling PR.
- Fork role: `contents: write` on the bot forks; pushes the rolling branch and
  mirrors the `.pot`.

Because no upstream repo may ever be granted `contents: write`, production uses
**two** separate Apps (the main-repo App carries `pull-requests: write` only).
For a single-maintainer test you may use one App with both permissions installed
on both accounts. Each role is configured by its App's **Client ID** (the legacy
numeric App ID is deprecated) and private key.

## Repository variables

Settings -> Secrets and variables -> Actions -> Variables:

| Variable | Example | Notes |
| --- | --- | --- |
| `L10N_BOT_FORK` | `<bot>/seedsigner` | Enables the sync job. Empty means no-op. |
| `L10N_TRANSLATIONS_BOT_FORK` | `<bot>/seedsigner-translations` | Empty means the mirror step is skipped. |
| `L10N_TRANSLATIONS_BRANCH` | `dev` | Branch Transifex reads source from. |
| `L10N_TRANSLATIONS_POT_PATH` | `l10n/messages.pot` | Source `.pot` path in the translations repo. |

## Repository secrets

| Secret | Value |
| --- | --- |
| `L10N_PR_CLIENT_ID` | PR App's Client ID |
| `L10N_PR_PRIVATE_KEY` | PR App's private key (`.pem` contents) |
| `L10N_FORK_CLIENT_ID` | Fork App's Client ID |
| `L10N_FORK_PRIVATE_KEY` | Fork App's private key (`.pem` contents) |

For a single-App test setup, put that App's Client ID and key in both pairs.
