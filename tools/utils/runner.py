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

import argparse
import os

class TestRunner:
    def check_input(self):
        parser = argparse.ArgumentParser(description="FFVVC test runner")

        parser.add_argument("test_path", type=str, nargs="+")
        parser.add_argument(
            "-f",
            "--ffmpeg-path",
            type=str,
            default=(os.getenv("FFMPEG_PATH") if os.getenv("FFMPEG_PATH") else None),
        )

        self.add_args(parser)

        self.args = parser.parse_args()

        not_vvdec = hasattr(self.args, "vvdec_path") and not self.args.vvdec_path
        if  not_vvdec and not self.args.vvdec_path and not self.args.ffmpeg_path:
            return Exception(
                "No FFmpeg path provided. Please provide a path to an FFmpeg executable either with -f, --ffmpeg-path or the environment variable FFMPEG_PATH."
            )
        return None

    def add_args(self, parser):
        pass

    @staticmethod
    def is_candidiate(f):
        filename, ext = os.path.splitext(f)
        ext = ext.lower()
        supported = [".bin", ".bit", ".vvc", ".266"]
        return ext in supported

    @staticmethod
    def list_files(path):
        l = []
        if os.path.isfile(path) and TestRunner.is_candidiate(path):
            l.append(path)
            return l
        for root, dirs, files in os.walk(path):
            for f in files:
                fn = os.path.join(root, f)
                if TestRunner.is_candidiate(fn):
                    l.append(fn)
        return l

    @property
    def files(self):
        l = []
        for path in self.args.test_path:
            l += TestRunner.list_files(path)
        return l
