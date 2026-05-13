# Install Local OaC Plugins

## Purpose

The plugin suite is repo-local and versioned with OaC. Marketplace metadata lives in `.agents/plugins/marketplace.json`; plugin roots live in `plugins/<plugin-name>`.

## Day0 Validation

```bash
cd ~/OaC
python3 scripts/validate_plugins.py
PYTHONPATH=src python3 scripts/quality_gate.py --profile standard
```

## Local Install Pattern

1. Open Codex with workspace `~/OaC`.
2. Confirm `.agents/plugins/marketplace.json` lists the desired plugins.
3. For notary-side Online HRA work, install `oac-cyberjack-rfid` before `oac-bnotk-xnp`, then install `oac-handelsregister`.
4. Install from the repo-local marketplace if supported by the Codex environment.
5. Confirm the installed card plugin display name is `OaC Card SAK Gate` and the source path is `./plugins/oac-cyberjack-rfid`.
6. Confirm the installed XNP plugin display name is `OaC Notary XNP Gate` and the source path is `./plugins/oac-bnotk-xnp`.
7. If the environment only supports home-local marketplaces, copy the reviewed plugin folders and marketplace entry after approval; keep the source of truth in this repository.

## Operational Boundary

The current plugins are installable skill plugins. They do not contain direct external write adapters, portal automation, card access, certificate handling or secret storage. Those require a separate reviewed connector PR.

For Online HRA, `oac-cyberjack-rfid` is the installable Card/SAK gate and `oac-bnotk-xnp` is the installable XNP readiness and authentication-gate companion. They do not authenticate as a notary by themselves, store PINs or notary credentials, trigger XNotar imports or submit filings.
