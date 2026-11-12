# kt-antigravity-plugin

Reuse a local **official `agy` sign-in** as a KohakuTerrarium provider.

The package declares one backend type, `google-antigravity-plugin`, and six
model presets. KohakuTerrarium shows it in **Settings → Providers → OAuth
sign-in** as **Google Antigravity (Plugin)**, right next to the built-in
Google Antigravity row. It never starts an OAuth flow, never asks for an API
key and never writes credential material anywhere.

## What you get

| Item | Value |
| --- | --- |
| Backend type | `google-antigravity-plugin` (own type; the built-in `google-antigravity` is untouched) |
| Settings row | `Google Antigravity (Plugin)` — "Reuse the local agy login." |
| Credentials | `external` — read-only borrow from `agy` |
| Native tools | none (agy exposes no provider-native tools) |
| Presets | `gemini-4-carbon`, `gemini-4-argon`, `gemini-3.8-flash`, `claude-opus-5-5`, `claude-sonnet-5-5`, `gpt-oss-120b` |

Existing configs that name `google-antigravity/...` keep using the built-in
provider. Nothing migrates and nothing is replaced.

## Requirements

- **Windows.** The credential lives in Windows Credential Manager (target
  `gemini:antigravity`) or in
  `~/.gemini/antigravity-cli/antigravity-oauth-token`. Any other platform
  reports `unsupported_platform`.
- **The official `agy` CLI, already signed in** to a consumer (not Cloud
  Code) account. This package only reads what `agy` owns.
- An `agy` account that is onboarded to the Cloud Code project used by the
  Antigravity CLI.

## Install

```bash
kt install @kt-antigravity-plugin            # marketplace
kt install E:\path\to\kt-antigravity-plugin -e   # local checkout, editable
kt list
```

Reload the Settings tab (or restart `kt serve`) after installing: the provider
list is rebuilt from the installed-package set.

Uninstall returns you to the built-in provider; sessions recorded with this
package stay readable because the signed history key and wire format are the
same:

```bash
kt uninstall kt-antigravity-plugin
```

## Use

```bash
kt run ./my-creature --llm google-antigravity-plugin/gemini-4-argon@reasoning=medium
kt doctor --llm google-antigravity-plugin/gemini-4-argon
```

Preset selectors work exactly like the built-in ones:

- `google-antigravity-plugin/<preset>` — default effort (`medium`)
- `@reasoning=low|medium|high`
- `@context=256k|512k|900k|840k|1048k|131k|80k` (depending on the preset)
- explicit wire ids such as `claude-opus-5-5-low` are accepted too

| Preset | Context choices | Output | Reasoning |
| --- | --- | ---: | --- |
| `gemini-4-carbon` | 256k, 512k, 900k | 65,536 | low, medium, high |
| `gemini-4-argon` | 256k, 512k, 900k | 65,536 | low, medium, high |
| `gemini-3.8-flash` | 256k, 1048k | 65,536 | low, medium, high |
| `claude-opus-5-5` | 256k, 840k | 128,000 | low, medium, high |
| `claude-sonnet-5-5` | 256k, 840k | 128,000 | low, medium, high |
| `gpt-oss-120b` | 80k, 131k | 32,768 | medium |

### Retired ids

v1 does **not** migrate the built-in provider's retired presets. They fail
fast with `deprecated_model, use <successor>`:

| Retired | Use instead |
| --- | --- |
| `gemini-3-flash`, `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.8-flash-tiered` | `gemini-3.8-flash` |
| `gemini-3.1-pro`, `gemini-pro-agent` | `gemini-4-argon` |
| `claude-sonnet-4-6` | `claude-sonnet-5-5` |
| `claude-opus-4-6-thinking` | `claude-opus-5-5` |

## Compliance

- No self-hosted OAuth: the plugin never contacts a Google auth endpoint to
  mint or exchange a token.
- Only the two documented local sources are read, once per request; refresh
  tokens are dropped on parse and access tokens are never logged, never
  written to sessions and never returned by any `status()` payload.
- Token renewal is delegated to `agy models`, serialized by
  `<config_dir>/locks/agy-refresh.lock`. A held lock surfaces as
  `refresh_busy`, never as an exception.

## Sign-in states

`Check status` calls `status()`, which the core normalizes to one of nine
states:

| State | Meaning / action |
| --- | --- |
| `ready` | A fresh access token was read. Nothing to do. |
| `expired` | Token expired but `agy` can renew it — refreshed automatically on the next request. |
| `login_required` | No credential found. Run `agy` and sign in. |
| `ambiguous_sources` | Keyring and the fallback file disagree. Remove one source. |
| `malformed_credential` | The stored blob is not a consumer token. Sign in with `agy` again. |
| `credential_store_unavailable` | The OS credential store refused the read. |
| `unsupported_platform` | Not Windows. |
| `refresh_busy` | Another process holds the refresh lock; try again shortly. |
| `unavailable` | Unexpected failure; check the server log. |

The row is host-local (`local_only: true`): on a worker node the action is
disabled and the API answers `400 local_host_only`.

## Troubleshooting

- `kt doctor --llm google-antigravity-plugin/gemini-4-argon` resolves the
  preset and prints the backend status line (`ready`, `login_required`, …).
- `kt list` shows the package; if the Settings row is missing, reload the
  page — the backend scan is cached per installed-package fingerprint.
- `history_requires_new_session` means a conversation carries signed assistant
  parts this package cannot replay (a different provider or account wrote
  them). Start a new session; do not hand-edit stored state.
- `custom_endpoint_not_supported`: presets on this backend cannot set
  `base_url` or `api_key_env`.

## Development

```bash
python -m pytest tests -q                 # unit + golden contract
python -m scripts.gen_presets             # rewrite llm_presets in kohaku.yaml
python -m scripts.gen_presets --check     # CI: manifest matches the catalogue
```

Layout:

```
kt_antigravity_login/
├── auth.py      # credential read + coordinated refresh (no OAuth)
├── client.py    # fixed-destination agy transport
├── format.py    # canonical messages <-> signed Google parts (STATE_KEY)
├── presets.py   # model families, limits, variation groups (PROVIDER name)
├── provider.py  # AntigravityProvider.from_profile / doctor
├── status.py    # AntigravityAuth: status / refresh / models / available
└── stream.py    # SSE decode + one signed turn
```

`kohaku.yaml` holds the backend entry and the **generated** `llm_presets`
block, so never edit that block by hand.
