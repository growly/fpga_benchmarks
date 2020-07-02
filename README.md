Benchmarks processed for Berkeley's Open Reconfigurable Architecture; no guarantee of portability whatsoever.

## How to run benchmarks ##

```
scripts/run_all.sh mcnc91/verilog
scripts/run_all.sh vtr/verilog
```

## How to collect results ##

```
scripts/collect_results.py --from_dir runs
```

This should generate a `.csv` for each device and grade for which there are results.
