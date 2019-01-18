import isp_run
import os
import re
import argparse
import isp_utils

def printUartOutput(run_dir):
    process_log = open(os.path.join(run_dir, "uart.log"))
    print("Process output:")
    print(process_log.read())


def getProcessExitCode(run_dir):
    process_log = open(os.path.join(run_dir, "uart.log"))
    process_out = process_log.readlines()
    hex_pattern = r"0x[0-9A-Fa-f]+$"
    for line in process_out:
        if "Progam has exited with code:" in line:
            matches = re.findall(hex_pattern, line)
            if matches is not None:
                return int(matches[0], 0)

    return -1


def main():
    parser = argparse.ArgumentParser(description="Run standalone ISP applications")
    parser.add_argument("exe_path", type=str, help='''
    Path of the executable to run
    ''')
    parser.add_argument("policy", type=str, help='''
    Name of the policy to run
    ''')
    parser.add_argument("-s", "--simulator", type=str, default="qemu", help='''
    Currently supported: qemu (default)
    ''')
    parser.add_argument("-r", "--runtime", type=str, default="hifive", help='''
    Currently supported: frtos, hifive (bare metal) (default)
    ''')
    parser.add_argument("-o", "--output", type=str, default="", help='''
    Default is current working directory.
    Location of simulator output directory. Contains supporting files and
    runtime logs.
    ''')
    parser.add_argument("-c", "--clean", action="store_true", help='''
    Remove all artifacts generated by this script
    ''')
    parser.add_argument("-u", "--uart", action="store_true", help='''
    Forward UART output from the simulator to stdout
    ''')
    parser.add_argument("-g", "--gdb", type=int, default=0, help='''
    Start the simulator in gdbserver mode
    ''')

    args = parser.parse_args()

    output_dir = args.output
    if args.output == "":
        output_dir = os.getcwd()

    exe_name = os.path.basename(args.exe_path)
    exe_full_path = os.path.abspath(args.exe_path)
    run_dir = os.path.join(output_dir, "isp_run_" + exe_name)
    isp_utils.removeIfExists(run_dir)
    if args.clean is True:
        return

    policy_full_name = isp_utils.getPolicyFullName(args.policy, args.runtime)

    print("Starting simulator...")
    result = isp_run.runSim(exe_full_path,
                            isp_utils.getKernelsDir(),
                            run_dir,
                            policy_full_name,
                            args.simulator,
                            ("", 16),
                            args.gdb)

    if args.uart is True:
        printUartOutput(run_dir)

    process_exit_code = getProcessExitCode(run_dir)
    print("Process exited with code {}".format(process_exit_code))

    if result is not isp_run.retVals.SUCCESS:
        print("Failed to build application: {}".format(result))


if __name__ == "__main__":
    main()
