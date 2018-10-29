#!/bin/bash

set -e
#set -x

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SRC=$script_dir/..
TESTDIR=$SRC/policies/policy_tests
#POLICIES="none stack rwx heap threeClass heap-rwx-stack-threeClass"
POLICIES="none stack rwx heap"
TEST=printf_works_1.c

export CONFIG=hifive
export SIM=qemu
export RULE_CACHE=finite

# Build hope-src, kernels, coremark
make -C $SRC -j4 all
make -C $SRC/policies/policy_tests clean-kernels install-kernels-simple
make -B -C $SRC/freedom-e-sdk software PROGRAM=coremark

for POLICY in ${POLICIES}; do
    # Clean and build test template dir
    cd $TESTDIR
    TARGET=osv.hifive.main.${POLICY}-${TEST}-O2
    rm -rf ./debug/${TARGET} && make debug-${TARGET}

    # Copy coremark to template dir and run in QEMU
    cp $SRC/freedom-e-sdk/software/coremark/coremark ./debug/${TARGET}/build/main
    make -C debug/${TARGET} inits
    time make -C debug/${TARGET} qemu

    # Print stats
    grep "Correct operation validated" debug/osv.hifive.main.${POLICY}-${TEST}-O2/uart.log || echo "Coremark run failed"
    grep hit debug/osv.hifive.main.${POLICY}-${TEST}-O2/qemu.log
done
