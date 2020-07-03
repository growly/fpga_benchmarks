#!/bin/bash

root=$(readlink -f "$( dirname "$( readlink -f "${BASH_SOURCE[0]}" )" )"/../)
yosys_benchmark_dir="${root}/yosys"

generate_files=$(find "${yosys_benchmark_dir}" -name generate.py)

for f in ${generate_files}; do
  location="$(dirname "${f}")"
  script="$(basename "${f}")"  # should be generate.py
  pushd "${location}"
  ./${script}
  popd
done
