#!/usr/bin/env python3
import os
import sys
import queue
import functools
import subprocess

from typing import TextIO, Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor

import click


class ParallelScheduler:
    @staticmethod
    def build_job_list(job_file):
        # type: (TextIO) -> List[Tuple[str, int]]
        mems = []
        cmds = []
        for idx, line in enumerate(job_file):
            line = line.strip()  # type: str
            if not line:
                continue
            if idx & 1:
                cmds.append(line)
            else:
                try:
                    mems.append(int(line))
                except ValueError:
                    raise RuntimeError(f"The memory footprint on line {idx + 1} is not parsable")

        if len(mems) != len(cmds):
            raise RuntimeError(f"In the job file, The number of memory constrains and commands does not match")
        return list(zip(cmds, mems))

    def __init__(self, job_file, max_memory, jobs, output_file):
        # type: (TextIO, int, int, Optional[TextIO]) -> None
        self.jobs_todo = self.build_job_list(job_file)

        self.num_total_jobs = len(self.jobs_todo)
        self.num_completed_jobs = 0
        self.num_dispatched_jobs = 0

        self.result_queue = queue.Queue()
        self.thread_pool_executor = ThreadPoolExecutor(max_workers=jobs)
        self.mem_avail = max_memory
        self.exe_avail = jobs
        self.output_file = output_file

        if jobs <= 0:
            raise RuntimeError("The maximum level of parallelism must >= 1")

        # prioritize the jobs with large memory footprint
        self.jobs_todo.sort(key=lambda _: _[1], reverse=True)
        if self.jobs_todo:
            j_mem_max = self.jobs_todo[0][1]
            if self.mem_avail < j_mem_max:
                raise RuntimeError(
                    f"This job list needs at least {j_mem_max} memory to schedule.\n"
                    f"But only {self.mem_avail} is allocated for it."
                )

    def run_job(self, cmd, mem):
        # type: (str, int) -> None
        ret_code = subprocess.call(
            cmd,
            shell=True,
            stdout=self.output_file,
            stderr=self.output_file
        )

        self.result_queue.put((cmd, mem, ret_code))

    def select_job(self):
        # type: () -> int
        if self.exe_avail > 0:
            for j_idx, (j_cmd, j_mem) in enumerate(self.jobs_todo):
                if self.mem_avail >= j_mem:
                    return j_idx
        return -1

    def dispatch_job(self, j_idx):
        # type: (int) -> None
        assert j_idx >= 0
        j_cmd, j_mem = self.jobs_todo[j_idx]

        assert self.exe_avail > 0
        assert self.mem_avail >= j_mem

        del self.jobs_todo[j_idx]
        self.exe_avail -= 1
        self.mem_avail -= j_mem

        j_func = functools.partial(self.run_job, j_cmd, j_mem)
        self.thread_pool_executor.submit(j_func)

        self.num_dispatched_jobs += 1

        print(f"\"{j_cmd}\" dispatched (alloc {j_mem} / left {self.mem_avail})")

    def complete_job(self, job_result):
        # type: (Tuple[str, int, int]) -> None
        j_cmd, j_mem, j_retcode = job_result
        print(f"\"{j_cmd}\" finished with code {j_retcode}.")

        self.exe_avail += 1
        self.mem_avail += j_mem

        self.num_completed_jobs += 1

    def schedule(self):
        # type: () -> None
        while True:
            j_idx = self.select_job()
            if j_idx < 0:
                break
            self.dispatch_job(j_idx)

    def start(self):
        while self.num_completed_jobs < self.num_total_jobs:
            self.schedule()
            job_result = self.result_queue.get(block=True)
            self.complete_job(job_result)

        self.thread_pool_executor.shutdown()


@click.command()
@click.argument("job-file", type=click.File())
@click.option("-m", "--max-memory", required=True, type=click.INT, help="Maximum usable RAM.")
@click.option("-j", "--jobs", required=True, type=click.INT, help="Maximum level of parallelism.")
@click.option("-o", "--output-file", required=False, type=click.File("w"), help="Dump STDOUT and STDERR to a file.")
@click.option("-C", "--directory", required=False, type=click.Path(exists=True, dir_okay=True, file_okay=False),
              help="Change to directory before execution any command")
def main(job_file, max_memory, jobs, directory, output_file):
    # type: (TextIO, int, int, str, Optional[TextIO]) -> None
    if directory:
        os.chdir(directory)

    try:
        scheduler = ParallelScheduler(job_file, max_memory, jobs, output_file)
        scheduler.start()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(-1)


if __name__ == '__main__':
    main()
