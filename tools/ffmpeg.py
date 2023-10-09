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
from runner import *

PASSED = 0
FAILED = 1
SKIPPED = 2
def print_files(name, files):
    if len(files) > 0:
        print(name + " files:")
        for f in files:
            print("    " + basename(f))

def print_summary(summary, count):
    summary[FAILED] = sorted(summary[FAILED], key =  lambda x: os.stat(x).st_size)
    print("")
    print("+++++++++ report +++++++++")
    print_files("failed", summary[FAILED])
    print_files("skipped", summary[SKIPPED])
    print_files("passed", summary[PASSED])
    print("")
    print(
        "total = "
        + str(count[PASSED] + count[FAILED] + count[SKIPPED])
        + ", passed = "
        + str(count[PASSED])
        + ", failed = "
        + str(count[FAILED])
        + ", skipped = "
        + str(count[SKIPPED])
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
        if os.path.isfile(self.args.test_path):
            self.__test_file()
        else:
            self.__test_dir()

    def add_args(self, parser):
        parser.add_argument("-t", "--threads", type=int, default=16)

    def __test_file(self):
        pss = self.__test(self.args.test_path)
        print(basename(self.args.test_path) + " passed" if pss == PASSED else " failed")
        return 0

    def __get_md5(self, input):
        cmd = self.args.ffmpeg_path + " -i " + input + " -vsync 0 -f md5 -"
        print(cmd)
        try:
            o = subprocess.run(cmd.split(), capture_output=True, timeout=5 * 60)
            if o.returncode:
                print(o.stderr)
                return ""
            return o.stdout.decode().replace("MD5=", "").strip()
        except Exception as e:
            return str(e)

    def __test(self, f):
        refmd5 = get_ref_md5(f)
        if not refmd5:
            print(basename(f) + " has no ref md5")
            return SKIPPED
        md5 = self.__get_md5(f)
        if refmd5 == md5:
            return PASSED

        print("md5 mismatch ref = " + refmd5 + " md5 = " + md5)
        return FAILED


    def __submmit_files(self, executor, path):
        future_to_file = {}
        for root, dirs, files in os.walk(path):
            for f in files:
                fn = join(root, f)
                if self.is_candidiate(fn):
                    future_to_file[executor.submit(self.__test, fn)] = fn
        return future_to_file


    def __test_dir(self):
        summary = [[], [], []]
        count = [0, 0, 0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.threads) as executor:
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
        sys.exit(count[FAILED])


if __name__ == "__main__":
    t = ConformanceRunner()
    t.check_input()
    t.run()
