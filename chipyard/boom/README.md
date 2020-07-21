## Benchmarks generated using Chipyard. ##

### Steps: ###

1. Clone and install chipyard per the [chipyard documentation](https://chipyard.readthedocs.io/en/latest/Chipyard-Basics/Initial-Repo-Setup.html):

```
# first, fetch dependencies
# second, do this:
git clone git@github.com:ucb-bar/chipyard
cd chipyard
CHIPYARD_ROOT=$(pwd)
./scripts/init-submodules-no-riscv-tools.sh
```

2. Generate BOOM configs for simulation:

```
cd ${CHIPYARD_ROOT}/sims/verilator
make verilog CONFIG=MediumBoomConfig
```

3. Dump all verilog files into one file. There will be references to simulation modules that do not exist, but they won't matter if the top module is set to the design top and not the chip or test harness tops.

```
cat ${CHIPYARD_ROOT}/sims/verilator/generated-src/chipyard.TestHarness.SmallBoomConfig/*.v >> SmallBoom.v
```

4. Determine the top module and write this to the `.top` file we have.

```
echo "DigitalTop" > SmallBoom.top
```
