# OpenSpec — PyKaraoke-NG

This directory holds the project's specifications, managed with
[OpenSpec](https://github.com/Fission-AI/OpenSpec).

* [`specs/`](specs/) — enduring capability specifications (how the product
  behaves today). Start with
  [`project-governance`](specs/project-governance/spec.md).
* [`changes/`](changes/) — proposed and in-progress changes, plus
  [`changes/archive/`](changes/archive/) for completed ones.
* [`config.yaml`](config.yaml) — project context for OpenSpec tooling.

The contributor workflow (propose → validate → implement → archive) is
documented on the website at
[`docs/contributing/openspec.md`](../docs/contributing/openspec.md) and
rendered at <https://wilsonify.github.io/pykaraoke-ng/contributing/openspec/>.

Quick check before opening a pull request:

```bash
npm install --global @fission-ai/openspec@1.14.1
openspec validate --all --strict
```
