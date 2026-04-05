# Experiments

Experiment configs and outputs for reproducible evaluation.

## Run a single experiment

```bash
python -m app.experiments.cli --config research/experiments/baseline.json --validate --report
```

## Run ablation grid

```bash
python -m app.experiments.cli --config research/experiments/baseline.json --ablation --validate
```

Outputs are written to `research/experiments/output/`.
Index and metrics exports are written to:
- `artifacts/experiments/output/index.json`
- `research/experiments/output/metrics.csv`

Use `--skip-index` or `--skip-export` to disable these post-processors.

## Run calibration search

```bash
python -m app.experiments.cli --config research/experiments/baseline.json --calibrate --calibration-config research/experiments/calibration.json
```

Calibration writes `research/experiments/output/calibration_summary.json`.

## Run Bayesian optimization

```bash
python -m app.experiments.cli --config research/experiments/baseline.json --optimize --optimization-config research/experiments/optimization.json
```

Optimization writes `research/experiments/output/optimization_summary.json`.

