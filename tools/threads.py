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

from dataclasses import dataclass
from itertools import product
import statistics
import subprocess
from utils.runner import *
from utils.perfapp import *

@dataclass
class ThreadTestRun:
    decoder: str
    sequence: str
    threads: int
    asm: bool
    fps: float

    def readable(self):
        return f"{self.sequence}, {self.decoder} {'asm' if self.asm else 'no asm'} {self.threads} threads: {self.fps} fps"

    def csv(self):
        return f"{self.decoder},{self.sequence},{self.threads},{self.asm},{self.fps}"

class ThreadRunner(TestRunner):
    __summary = {}
    __app = None
    def run(self):
        self.__app = self.__get_app()

        files = self.list_files(self.args.test_path)
        for f in files:
            self.__test(f)

        print()
        self.__print_summary()

    def add_args(self, parser):
        parser.add_argument("--vvdec-path", type=str)
        parser.add_argument("--csv", action="store_true")

    def __get_app(self):
        if self.args.vvdec_path:
            return VVDecApp(self.args.vvdec_path)
        return FFmpegApp(self.args.ffmpeg_path)

    def __test(self, input):
        fn = os.path.basename(input)
        self.runs = []

        for asm, threads in product([True, False], [1, 2, 4, 8, 16]):
            self.__app.set_asm(asm)
            self.__app.set_threads(threads)
            cmd = self.__app.get_cmd(input)
            print(cmd)
            try:
                o = subprocess.run(cmd.split(), capture_output=True, timeout=5 * 60)
                if o.returncode:
                    raise Exception(o.stderr)
                o = self.__app.get_fps(o)
                print("fps = ", o)
            except Exception as e:
                print(e)
                raise

            run = ThreadTestRun("vvdec" if self.args.vvdec_path else "ffvvc", fn, threads, asm, o)
            self.runs.append(run)

    def __print_summary(self):
        if self.args.csv:
            print("Decoder,Sequence,Threads,SIMD,FPS")

        for run in self.runs:
            if not self.args.csv:
                print(run.readable())
            else:
                print(run.csv())

if __name__ == "__main__":
    t = ThreadRunner()
    t.check_input()
    t.run()
