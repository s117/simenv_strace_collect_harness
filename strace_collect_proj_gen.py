#!/usr/bin/env python3
import os
import operator
import sys
from math import floor
from typing import Optional

import yaml
import click as click
from bashlex import parser, ast
from bashlex.errors import ParsingError

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def add_prefix_to_stdin_file_in_shcmd(shcmd, prefix):
    # type: (str, str) -> Optional[str]
    trees = parser.parse(shcmd)
    insert_positions = []

    class nodevisitor(ast.nodevisitor):
        def visitredirect(self, n, input, type, output, heredoc):
            if type == "<" and len(output.parts) == 0:
                insert_positions.append(output.pos[0])
            else:
                print("Warning: command [%s] contains non-resolvable stdin source." % shcmd)

    try:
        for tree in trees:
            visitor = nodevisitor()
            visitor.visit(tree)
    except ParsingError:
        return None

    insert_positions.sort(reverse=True)
    result_cmd = shcmd
    for ins_pos in insert_positions:
        result_cmd = f"{result_cmd[:ins_pos]}{prefix}{result_cmd[ins_pos:]}"
    return result_cmd


def hours_to_hm_str(hrs):
    # type: (float) -> str
    h = floor(hrs)
    m = floor((hrs - h) * 60)
    return "%d:%d" % (h, m)


@click.command()
@click.argument("path-to-all-sysroot", type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.argument("output-path", type=click.Path(exists=False, dir_okay=True, file_okay=False))
@click.option("-s", "--skip-sysroot-check", is_flag=True)
def main(path_to_all_sysroot, output_path, skip_sysroot_check):
    riscv_install = os.getenv("RISCV", None)
    if not riscv_install or not os.path.isdir(riscv_install):
        print("RISCV environmental variable is not set to a installed toolchain")
        sys.exit(-1)

    with open(os.path.join(SCRIPT_DIR, "app_info.yaml")) as fp_app_info:
        apps_info = yaml.safe_load(fp_app_info)

    with open(os.path.join(SCRIPT_DIR, "Makefile.template.mk"))as fin:
        mk_template = fin.read()
    with open(os.path.join(SCRIPT_DIR, "job_bsub.template.bash"))as fin:
        bsub_job_template = fin.read()
    mk_template_config = {
        "app_name": "",
        "app_cmd": "",
        "app_memsize": "",
        "app_pristine_sysroot": "",
        "app_init_cwd": "/app",
        "fesvr_flags": "+strace=./syscall.trace +std-dump=./console",
        "sim_cmd": "spike",
        "sim_flags": "",
        "pk_flags": "",
    }
    bjob_template_config = {
        "job_name": "",
        "time_limit": "",
        "memory_limit": "",
        "riscv_bin_path": os.path.join(riscv_install, "bin")
    }

    generated_runs = []

    for app_name, app_info in apps_info.items():
        os.makedirs(os.path.join(output_path, app_name), exist_ok=True)
        mk_template_config["app_name"] = app_name
        mk_template_config["app_cmd"] = add_prefix_to_stdin_file_in_shcmd(
            app_info["cmd"],
            "$(SIMENV_SYSROOT)/$(APP_INIT_CWD)/"
        )
        mk_template_config["app_memsize"] = app_info["memory"]
        mk_template_config["app_pristine_sysroot"] = \
            os.path.abspath(
                os.path.join(path_to_all_sysroot, app_info["sysroot"])
            )
        bjob_template_config["job_name"] = app_name
        bjob_template_config["memory_limit"] = app_info["memory"] + 512
        bjob_template_config["time_limit"] = hours_to_hm_str(app_info["estimated_time"] * 1.5)

        if not skip_sysroot_check and not os.path.isdir(mk_template_config["app_pristine_sysroot"]):
            raise RuntimeError(f"Fatal: app path {mk_template_config['app_pristine_sysroot']} doesn't exist!")

        with open(os.path.join(output_path, app_name, "Makefile"), "w") as fout:
            fout.write(mk_template.format(**mk_template_config))

        with open(os.path.join(output_path, app_name, "job_bsub.sh"), "w") as fout:
            fout.write(bsub_job_template.format(**bjob_template_config))

        generated_runs.append((app_name, app_info["memory"]))

    generated_runs.sort(key=operator.itemgetter(1, 0))

    with open(os.path.join(output_path, "mparallel.jobs"), "w") as fout:
        sim_cmd = "cd {a_name}; make clean; make envsetup; make run"
        for a_name, a_mem in generated_runs:
            print(f"{a_mem}", file=fout)
            print(sim_cmd.format(a_name=a_name), file=fout)


if __name__ == '__main__':
    main()
