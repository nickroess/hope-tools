import functools
import itertools
import operator
import subprocess
import os
import shutil
import time
import glob
import errno
import logging

from isp_utils import *
import isp_qemu
import isp_renode

# backend helper to run an ISP simulation with a binary & kernel
# TODO: runFPGA support

logger = logging.getLogger()

# possible module outcomes
class retVals:
    NO_BIN = "No binary found to run"
    NO_POLICY = "No policy found"
    TAG_FAIL  = "Tagging tools did not produce expected output"
    SUCCESS   = "Simulator run successfully"

# -- MAIN MODULE FUNCTIONALITY

# arguments:
#  exe_path - path to executable to be run
#  kernels_dir - directory containing PEX kernels
#  run_dir - output of this module. Directory to put supporting files, run
#    the simulation, and store the appropriate logs
#  policy - name of the policy to be run
#  sim - name of the simultator to use
#  rule_cache - rule cache configuration tuple. (cache_name, size)
#  gdb - debug port for gdbserver mode (optional)
#  tag_only - run the tagging tools without running the simulator
#  extra - extra command line arguments to the simulator

def runSim(exe_path, kernels_dir, run_dir, policy, sim, runtime, rule_cache, gdb, tag_only, extra):
    exe_name = os.path.basename(exe_path)

    if not os.path.isfile(exe_path):
        return retVals.NO_BIN

    policy_dir = policy
    if not os.path.isdir(policy):
        policy_dir = getPolicyDir(policy, kernels_dir)
        if policy_dir is None:
            logger.error("Failed to find directory for policy")
            return retVals.NO_POLICY

    doMkDir(run_dir)

    print("doValidatorCfg()")
    doValidatorCfg(policy_dir, run_dir, exe_name, rule_cache)
    print("doEntititesFile()")
    doEntitiesFile(run_dir, exe_name)
    print("generateTagInfo()")    
    generateTagInfo(exe_path, run_dir, policy_dir)
    print("Rebuild validator()")
    rebuildValidator(kernels_dir, policy, run_dir)

    bininfo_base_path = os.path.join(run_dir, "bininfo", exe_name) + ".{}"
    if not os.path.isfile(bininfo_base_path.format("taginfo")) or \
       not os.path.isfile(bininfo_base_path.format("text"))    or \
       not os.path.isfile(bininfo_base_path.format("text.tagged")):
        return retVals.TAG_FAIL

    if tag_only is True:
        return retVals.SUCCESS

    if sim == "qemu":
        isp_qemu.runOnQEMU(exe_path, run_dir, policy_dir, runtime, gdb, extra)
    elif sim == "renode":
        isp_renode.runOnRenode(exe_path, run_dir, policy_dir, runtime, gdb)

    return retVals.SUCCESS

# After running the policy-specific parts of the toolflow (e.g., generateTagInfo),
# we do another Make on the validator. This gives the toolflow a chance to
# integrate application-specific tagging info into compiled kernel. Optional.
def rebuildValidator(kernels_dir, policy, run_dir):
    
    # Run make in the engine directory
    kernel_dir = os.path.join(kernels_dir, policy)
    engine_dir = os.path.join(kernel_dir, "engine")
          
    subprocess.Popen(["make", "-f", "Makefile.isp"],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,
                     cwd=engine_dir).wait()

    # Then copy the new validator .so up to the top level
    build_dir = os.path.join(engine_dir, "build")
    for so_file in glob.glob(build_dir + "/*.so"):
        shutil.copy(so_file, kernel_dir)


def getPolicyDir(policy, kernels_dir):
    isp_kernel_cmd = "isp_kernel"
    isp_kernel_args = [policy, "-o", kernels_dir]

    policy_dir = os.path.join(kernels_dir, policy)
    if not os.path.isdir(policy_dir):
        logger.info("Attempting to compile missing policy")
        subprocess.Popen([isp_kernel_cmd] + isp_kernel_args).wait()
    else:
        return policy_dir

    if not os.path.isdir(policy_dir):
        logger.error("Failed to compile missing policy")
        return None

    logger.info("Successfully compiled missing policy")
    return policy_dir


def generateTagInfo(exe_path, run_dir, policy_dir):
    policy = os.path.basename(policy_dir).split("-debug")[0]
    exe_name = os.path.basename(exe_path)
    doMkDir(os.path.join(run_dir, "bininfo"))
    with open(os.path.join(run_dir, "inits.log"), "w+") as initlog:
        subprocess.Popen(["gen_tag_info",
                          "-d", policy_dir,
                          "-t", os.path.join(run_dir, "bininfo", exe_name + ".taginfo"),
                          "-b", exe_path,
                          "-e", os.path.join(policy_dir, policy + ".entities.yml"),
                          os.path.join(run_dir, exe_name + ".entities.yml")],
                          stdout=initlog, stderr=subprocess.STDOUT, cwd=run_dir).wait()


def doEntitiesFile(run_dir, name):
    filename = os.path.join(run_dir, (name + ".entities.yml"))
    if os.path.exists(filename) is False:
        open(filename, "a").close()


def doValidatorCfg(policy_dir, run_dir, exe_name, rule_cache):
    rule_cache_name = rule_cache[0]
    rule_cache_size = rule_cache[1]
    soc_cfg = "hifive_e_cfg.yml"

    validatorCfg =  """\
---
   policy_dir: {policyDir}
   tags_file: {tagfile}
   soc_cfg_path: {soc_cfg}
""".format(policyDir=policy_dir,
           tagfile=os.path.join(run_dir, "bininfo", exe_name + ".taginfo"),
           soc_cfg=os.path.join(policy_dir, "soc_cfg", soc_cfg))

    if rule_cache_name != "":
        validatorCfg += """\
   rule_cache:
      name: {rule_cache_name}
      capacity: {rule_cache_size}
        """.format(rule_cache_name=rule_cache_name, rule_cache_size=rule_cache_size)

    with open(os.path.join(run_dir, "validator_cfg.yml"), 'w') as f:
        f.write(validatorCfg)
