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

3. Remove modules with weird verilog, such as those intended for the simulator to read.

4. Dump all verilog files into one file. There will be references to simulation modules that do not exist, but they won't matter if the top module is set to the design top and not the chip or test harness tops.

Remember also that github has a 50MB size limit.

5. Determine the top module and write this to the `.top` file we have.

```
for size in Small Medium Large Mega; do
  ls ${CHIPYARD_ROOT}/sims/verilator/generated-src/chipyard.TestHarness.${size}BoomConfig/*.v | grep -Ev 'Sim.*\.v' | xargs cat > ${size}Boom.v;
  echo "DigitalTop" > ${size}Boom.top;
  tar -Jcf ${size}Boom.tar.xz ${size}Boom.v
done
```

6. Our scripts can sometimes deal with `gzip`'d verilog source files, but we have to be careful about which version of `gzip`/`gunzip` we rely on. To avoid that, these files are encoded with tar. So decompress with tar too:

```
for file in *.tar.xz; do
  tar -Jxf ${f} &
done
