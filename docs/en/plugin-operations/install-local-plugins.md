# Install Local NaC Plugins

## Purpose

The plugin suite is repo-local and versioned with NaC. Marketplace metadata lives in `.agents/plugins/marketplace.json`; plugin roots live in `plugins/<plugin-name>`.

## Day0 Validation

```bash
cd ~/NaC
python3 scripts/validate_plugins.py
python3 scripts/install_local_plugins.py --mode link
PYTHONPATH=src python3 scripts/quality_gate.py --profile standard
```

After the install step, quit Codex and reopen it with workspace `~/NaC`. A
running session reads active tools and plugins at startup; repo-local plugins
are not injected into an already running session.

## Why A Session Shows No Plugins

If the plugin folders exist locally but the current session shows no plugins,
two layers are out of sync:

1. The repository contains the source of truth:
   `.agents/plugins/marketplace.json` and `plugins/`.
2. The local Codex environment also needs a discovery mirror inside the
   home-local plugin root. Without that mirror, or without restarting after the
   mirror is written, a new session will not see the repo-local plugins.

`scripts/install_local_plugins.py --mode link` mirrors the marketplace to
`~/.agents/plugins/marketplace.json`. Plugin folders are linked under
`~/plugins/<plugin>`. Set `NAC_PLUGIN_HOME=/other/root` to use a different home
root; marketplace and plugins then live below that root. Link mode is the
development default because the repository remains the only source of truth. If
an environment does not allow symlinks, use `--mode copy` as the fallback.

If `~/.agents` is mounted read-only in a managed Codex session, run the install
step in the host workspace or on the actual workstation. For integration checks
only, use a writable test root with `--target-root /tmp/nac-plugin-home`; for
real Codex discovery, the home-local root remains authoritative.

## Local Install Pattern

1. Open Codex with workspace `~/NaC`.
2. Confirm `.agents/plugins/marketplace.json` lists the desired plugins.
3. Run `python3 scripts/install_local_plugins.py --mode link`.
4. Restart Codex or open a new session with workspace `~/NaC`.
5. For notary-side Online HRA work, install `nac-cyberjack-rfid` before `nac-bnotk-xnp`, then install `nac-handelsregister`.
6. Install from the repo-local marketplace if supported by the Codex environment.
7. Confirm the installed card plugin display name is `Karte/SAK` and the source path is `./plugins/nac-cyberjack-rfid`.
8. Confirm the installed XNP plugin display name is `XNP-Prüfung` and the source path is `./plugins/nac-bnotk-xnp`.
9. If an environment accepts copies but not symlinks, run `python3 scripts/install_local_plugins.py --mode copy --force` after approval; keep the source of truth in this repository.

## Operational Boundary

The current plugins are installable skill plugins. They do not contain direct external write adapters, portal automation, card access, certificate handling or secret storage. Those require a separate reviewed connector PR.

For Online HRA, `nac-cyberjack-rfid` is the installable `Karte/SAK`, and `nac-bnotk-xnp` is the installable `XNP-Prüfung`. They do not authenticate as a notary by themselves, store PINs or notary credentials, trigger XNotar imports or submit filings.
