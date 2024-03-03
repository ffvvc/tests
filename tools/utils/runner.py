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
import hashlib
import os
import urllib.request
import yaml
import tqdm

class TestRunner:
    def check_input(self):
        parser = argparse.ArgumentParser(description="FFVVC test runner")

        parser.add_argument("test_path", type=str)
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
    def get_cfg(file):
        cfg_file = os.path.splitext(file)[0] + ".yaml"
        try:
            with open(cfg_file, "r") as f:
                cfg = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"No corresponding config YAML file {cfg_file} found for source file {file}")
        return cfg

    @staticmethod
    def get_md5(file):
        md5 = hashlib.md5()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    @staticmethod
    def check_src_md5(file):
        cfg = TestRunner.get_cfg(file)
        md5 = cfg["src_md5"]
        return md5 == TestRunner.get_md5(file)

    @staticmethod
    def child_files(path):
        if os.path.isfile(path):
            return [path]
        else:
            return [os.path.join(dirpath, filename)
                    for dirpath, _, filenames in os.walk(path)
                    for filename in filenames]

    @staticmethod
    def is_candidiate(f):
        filename, ext = os.path.splitext(f)
        ext = ext.lower()
        supported = [".bin", ".bit", ".vvc", ".266"]
        return ext in supported

    @staticmethod
    def list_files(path):
        TestRunner.update_files(path)
        return [f for f in TestRunner.child_files(path) if TestRunner.is_candidiate(f)]

    @staticmethod
    def download(file):
        dest = file + ".bit"
        cfg = TestRunner.get_cfg(file)
        url = cfg["url"]
        pbar = tqdm.tqdm(desc=f"Downloading {dest}",
                         unit="B", unit_scale=True, miniters=1, dynamic_ncols=True)
        def update_bar(blocknum, blocksize, totalsize):
            pbar.total = totalsize
            pbar.update(blocknum * blocksize - pbar.n)
        filename, headers = urllib.request.urlretrieve(url, dest, reporthook=update_bar)
        return filename

    @staticmethod
    def update_files(path):
        files = [f for f in TestRunner.child_files(path) if f.endswith(".yaml")]
        files = [os.path.splitext(f)[0] for f in files]

        for f in files:
            for ext in [".bin", ".bit", ".vvc", ".266"]:
                if os.path.isfile(f + ext):
                    src = f + ext
                    break
            else:
                src = TestRunner.download(f)

            if not TestRunner.check_src_md5(src):
                raise Exception(f"Source MD5 mismatch for {src}")
