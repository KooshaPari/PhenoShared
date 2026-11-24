# AGENTS.md generator

`docs/scripts/render-agents-md.sh` renders an `AGENTS.md` file from a minimal `pheno-agents-md.yaml` config.

## Usage

```bash
./docs/scripts/render-agents-md.sh [config] [output] [repo-name]
```

- `config`: defaults to `./pheno-agents-md.yaml`
- `output`: defaults to `./AGENTS.md`
- `repo-name`: defaults to the repository directory name

## Config keys

- `build`
- `test`
- `lint`
- `audit`
- `sign`
- `repo_name`
- `extra_dont_touch`

## Notes

- The script is intentionally lightweight and shell-friendly.
- It exists to keep the handbook repo as the home for agent-governance material without keeping a separate `pheno-agents-md` repository alive.
