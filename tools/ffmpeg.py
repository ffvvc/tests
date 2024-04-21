#!/usr/bin/env python3
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import sys
import os
from os.path import dirname, join, realpath, basename
from sys import platform
import re
import concurrent.futures
import subprocess
from utils.runner import *
from enum import Enum, auto
from collections import defaultdict


class TestResult(Enum):
    PASSED = auto()
    MISMATCH = auto()
    SKIPPED = auto()
    TIMEOUT = auto()
    SEGFAULT = auto()
    PANIC = auto()
    FPE = auto()
    DECODE_ERR = auto()


def print_files(name, files):
    if len(files) > 0:
        print(name + " files:")
        for f in files:
            print("    " + basename(f))


def print_summary(summary, count):
    failed = sum(
        count[status]
        for status in count.keys()
        if status not in [TestResult.PASSED, TestResult.SKIPPED]
    )
    summary[TestResult.PASSED].sort(key=lambda x: basename(x))
    summary[TestResult.MISMATCH].sort(key=lambda x: os.stat(x).st_size)
    print("")
    print("+++++++++ report +++++++++")
    print_files("skipped", summary[TestResult.SKIPPED])
    print_files("mismatch", summary[TestResult.MISMATCH])
    print_files("timeout", summary[TestResult.TIMEOUT])
    print_files("segfault", summary[TestResult.SEGFAULT])
    print_files("panic", summary[TestResult.PANIC])
    print_files("floating-point exception", summary[TestResult.FPE])
    print_files("decode_err", summary[TestResult.DECODE_ERR])
    print("")
    print(
        "total = "
        + str(sum(count.values()))
        + ", passed = "
        + str(count[TestResult.PASSED])
        + ", skipped = "
        + str(count[TestResult.SKIPPED])
        + ", failed = "
        + str(failed)
    )
    print("----------")


def get_ref_md5(fn):
    dir = dirname(fn)
    name = basename(fn)
    checksums_path = os.path.join(dir, "md5.txt")
    try:
        with open(checksums_path) as checksums_file:
            checksums = checksums_file.readlines()
        checksums = filter(lambda l: l.endswith("  " + name + "\n"), checksums)
        checksum = next(checksums)
        return checksum.split()[0]
    except (FileNotFoundError, StopIteration):
        return None


class ConformanceRunner(TestRunner):
    def run(self):
        if self.args.allow_decode_error and not self.args.no_output_check:
            raise Exception("--allow-decode-error requires --no-output-check")

        summary = defaultdict(list)
        count = defaultdict(int)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.args.threads
        ) as executor:
            future_to_file = self.__submmit_files(executor, self.args.test_path)
            for future in concurrent.futures.as_completed(future_to_file):
                f = future_to_file[future]
                try:
                    s = future.result()
                except Exception as e:
                    print("%s generated an exception: %s" % (f, e))
                else:
                    count[s] += 1
                    summary[s].append(f)

        print_summary(summary, count)
        sys.exit(count[TestResult.MISMATCH])

    def add_args(self, parser):
        parser.add_argument("-t", "--threads", type=int, default=16)
        parser.add_argument("--allow-decode-error", action="store_true")
        parser.add_argument("--no-output-check", action="store_true")

    def __ffmpeg_cmd(self, input_stream):
        return (
            self.args.ffmpeg_path
            + " -strict -2 -i "
            + input_stream
            + " -vsync 0 -noautoscale -f md5 -"
        )

    @staticmethod
    def __returncode_err(returncode):
        if returncode == -11:
            return TestResult.SEGFAULT
        elif returncode == -6:
            return TestResult.PANIC
        elif returncode == -8:
            return TestResult.FPE
        else:
            print(returncode)
            return TestResult.DECODE_ERR

    def __test(self, f):
        print(basename(f), end="")

        if not self.args.no_output_check:
            refmd5 = get_ref_md5(f)
            if not refmd5:
                print(" has no ref md5")
                return TestResult.SKIPPED

        cmd = self.__ffmpeg_cmd(f)
        try:
            process = subprocess.run(cmd.split(), capture_output=True, timeout=30 * 60)
        except subprocess.TimeoutExpired:
            print(" timed out")
            return TestResult.TIMEOUT

        if process.returncode != 0:
            if self.args.allow_decode_error and process.returncode > 0:
                print(" passed")
                return TestResult.PASSED
            else:
                print(" failed")
                return self.__returncode_err(process.returncode)

        if not self.args.no_output_check:
            md5 = process.stdout.decode().replace("MD5=", "").strip()
            if refmd5 != md5:
                print(" MD5 mismatch. Ref MD5 = " + refmd5 + ", decoded MD5 = " + md5)
                return TestResult.MISMATCH

        print(" passed")
        return TestResult.PASSED

    def __submmit_files(self, executor, path):
        future_to_file = {}
        file_list = sorted(self.list_files(path), key=lambda x: os.stat(x).st_size)
        for f in file_list:
            future_to_file[executor.submit(self.__test, f)] = f

        return future_to_file


if __name__ == "__main__":
    t = ConformanceRunner()
    t.check_input()
    t.run()
