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
import re
import statistics
import subprocess
import sys
from runner import *

class PerformanceRunner(TestRunner):
    __summary = {}
    def run(self):
        path = self.args.test_path
        if os.path.isfile(path):
            self.__test_file(path)
        else:
            self.__test_dir(path)
        self.__print_summary()

    def __test_dir(self, path):
        files = self.list_files(path)
        for f in files:
            self.__test(f)

    def __test_file(self, path):
        self.__test(path)

    def __test(self, input):
        fn = os.path.basename(input)
        self.__summary[fn] = []
        fps = self.__summary[fn]
        nul = "NUL" if sys.platform == 'win32' else "/dev/null"
        cmd = self.args.ffmpeg_path + " -i " + input + " -vsync 0 -y -f rawvideo " + nul
        print(cmd)
        for i in range(0, 3):
            try:
                o = subprocess.run(cmd.split(), capture_output=True, timeout=5 * 60)
                if o.returncode:
                    raise Exception(o.stderr)
                o = re.findall(r'fps=.*?q',o.stderr.decode())[-1]
                o = float(o.replace("fps=", "").replace("q", "").strip())
                print("fps = ", o)
                fps.append(o)
            except Exception as e:
                print(e)
                raise

    def __print_summary(self):
        for k,v in self.__summary.items():
            check_coefficient_of_variation(k, v)
            print(k, "|", "%.1f"%statistics.fmean(v), "|")
        pass

def check_coefficient_of_variation(k, v):
    mean = statistics.fmean(v)
    if mean > 0:
        cv = statistics.stdev(v) / mean
        if (cv > 0.1):
            print("cv is high for " + k + ", " + str(v))

if __name__ == "__main__":
    t = PerformanceRunner()
    t.check_input()
    t.run()
