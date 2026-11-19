# Quick start

Use Python 3.11+, uv, and Node 22.12+ under Linux/WSL. From the repository root:

```bash
make install
make models
make dev
```

Open http://localhost:5173. Acquire the real products and XML label declared in `data/metadata/demo_pair.json` from official providers, then select the available real scene. Missing imagery never triggers mocked data. A completed job may be scientifically rejected; inspect coverage, native correspondences and quality reasons.

See [COMMANDS.md](../COMMANDS.md) for every CLI/API/test/benchmark/deployment command and [current verification](production_readiness_report.md) for measured limitations. Public release remains blocked by scientific validation and rights/licensing review.
