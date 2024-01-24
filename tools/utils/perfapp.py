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
class PerfApp:
    def __init__(self, path):
        self._asm  = True
        self._threads = 0
    def set_asm(self, enabled):
        self._asm = enabled
    def set_threads(self, threads):
        self._threads = threads

class FFmpegApp(PerfApp):
    def __init__(self, path):
        super().__init__(self)
        self.__path = path
        pass
    def get_cmd(self, input):
        extra = " " if self._asm else " -cpuflags 0"
        extra += " -threads " + str(self._threads) if self._threads else ""
        cmd = self.__path + extra + " -i " + input + " -vsync 0 -y -f null - "
        return cmd
    def get_fps(self, o):
        o = re.findall(r'fps=.*?q',o.stderr.decode())[-1]
        o = float(o.replace("fps=", "").replace("q", "").strip())
        return o
    def get_name(self):
        return "ffmpeg"

class VVDecApp(PerfApp):
    def __init__(self, path):
        super().__init__(self)
        self.__path = path
        pass
    def get_cmd(self, input):
        extra = " " if self._asm else " --simd 0"
        extra += " -t " + str(self._threads) if self._threads else ""
        cmd = self.__path + extra + " -b " + input
        return cmd
    def get_fps(self, o):
        o = re.findall(r'@ .*?fps',o.stdout.decode())[0]
        o = float(o.replace("fps", "").replace("@", "").strip())
        return o
    def get_name(self):
        return "vvdec"

class OpenVVCApp(PerfApp):
    def __init__(self, path):
        super().__init__(self)
        self.__path = path
        pass
    def get_cmd(self, input):
        extra_pre = "time "
        extra_post = " -t " + str(self._threads) if self._threads else " "
        extra_post += " -e " + str(self._threads) if self._threads else " "
        extra_post += " -i " + input
        extra_post += " -o /dev/null"
        cmd = extra_pre + self.__path + extra_post
        return cmd
    def get_fps(self, o):
        if match := re.search(r"Decoded ([0-9]+) pictures", o.stderr.decode()):
            frame_count = int(match.group(1))
        else:
            raise Exception("No frame count found")
        if match := re.search(r"([0-9]+):([0-9]{2}).([0-9]{2})elapsed", o.stderr.decode()):
            rtime_m = int(match.group(1))
            rtime_s = int(match.group(2))
            rtime_cs = int(match.group(3))
            rtime = rtime_m * 60 + rtime_s + rtime_cs / 100
        else:
            raise Exception("No time found")
        return frame_count / rtime
    def get_name(self):
        return "openvvc"
