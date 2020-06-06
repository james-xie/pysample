import os
import sys
import optparse

from builtins import exec
from typing import Any

from pysample.sampler import sample
from pysample.timer import stop_timer, timer_started


def find_script(script_name: str) -> str:
    """
    Find the script. If the input is not a file, then $PATH will be searched.
    """
    if os.path.isfile(script_name):
        return script_name
    path = os.getenv("PATH", os.defpath).split(os.pathsep)
    for dir in path:
        if dir == "":
            continue
        fn = os.path.join(dir, script_name)
        if os.path.isfile(fn):
            return fn

    sys.stderr.write(f"Could not find script {script_name}\n")
    raise SystemExit(1)


def execute_script(script_name: str, options: Any):
    sampler = sample(options.interval, 0, options.outfile)

    ctx = None
    try:
        print(f"Executing the given script {script_name}")
        with open(script_name, "rb") as f:
            code_object = compile(f.read(), script_name, "exec")
            # Start to sampling
            ctx = sampler.begin(script_name)
            globals_ctx = locals_ctx = {"__name__": script_name}
            exec(code_object, globals_ctx, locals_ctx)
    finally:
        if ctx:
            sampler.end(ctx)
        if timer_started():
            stop_timer()
        print(f"Wrote sampling result to {options.outfile}")


def main():
    globals()["__name__"] = "pysample.main"

    usage = "%prog [-o output_file_path] [-i sampling_interval] python_script [arg] ..."
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-o", "--outfile", default=None, help="Save sampling result to 'outfile'."
    )
    parser.add_option(
        "-i",
        "--interval",
        default=10,
        type="int",
        help="Sampling interval (in milliseconds), The minimum value is 5.",
    )

    if len(sys.argv) < 2:
        parser.print_usage()
        sys.exit(2)

    options, args = parser.parse_args()

    if not options.outfile:
        basename = os.path.basename(args[0])
        options.outfile = f"{basename}.txt"

    if options.interval < 5:
        options.interval = 5

    sys.argv[:] = args
    script_name = find_script(sys.argv[0])
    # Make sure the script's directory is on sys.path
    sys.path.insert(0, os.path.dirname(script_name))

    execute_script(script_name, options)


if __name__ == "__main__":
    main()
