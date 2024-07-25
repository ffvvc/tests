import hashlib
import argparse
import time
import os
import zipfile
import subprocess
import shutil

def get_file_md5(path):
    with open(path, 'rb') as f:
        data = f.read()
        file_md5 = hashlib.md5(data).hexdigest()
        return file_md5
    return ''

def list_files(dir):
    files = []
    paths = os.walk(dir)
    for path, dir_lst, file_lst in paths:
        for f in file_lst:
            files.append(os.path.join(path, f))
    return files

def remove_dir(dir):
    paths = os.walk(dir)
    for path, dir_lst, file_lst in paths:
        for f in file_lst:
            os.remove(os.path.join(dir, f))
        for d in dir_lst:
            remove_dir(os.path.join(dir, d))
    os.rmdir(dir)

class MD5Runner():
    def __init__(self) -> None:
        parser = argparse.ArgumentParser(description='md5 generator')
        parser.add_argument('-f', '--ffmpeg',      type=str, required=True,  default=None, help='path to ffmpeg.exe path')
        parser.add_argument('-v', '--vvdec',       type=str, required=False, default=None, help='path to vvdecapp.exe'   )
        parser.add_argument('--clips',             type=str, required=True,  default=None, help='path to vtm clips'      )
        parser.add_argument('--failure_path',      type=str, required=True,  default=None, help='the destination path when the md5 is not match between ffmpeg and vvdec')
        parser.add_argument('--conformance_path',  type=str, required=True,  default=None, help='the destination path when the md5 is match between ffmpeg and vvdec'    )
        self.args = parser.parse_args()

        self.failed_path = ['conformance/failed/v1', 'conformance/failed/v2']
        self.passed_path = ['conformance/passed/v1', 'conformance/passed/v2']

        self.failed = []
        self.passed = []

        for p in self.failed_path:
            self.failed.append(self.read_md5(p))

        for p in self.passed_path:
            self.passed.append(self.read_md5(p))
        pass

    def read_md5(self, path):
        path = os.path.join(os.path.abspath(__file__), '../../' + path)
        md5_list = {}
        with open(os.path.join(path, 'md5.txt'), 'r+') as f:
            for line in f.readlines():
                pair = line.replace('\n', '').split('  ')
                if len(pair) == 2:
                    md5, name = pair
                    md5_list[name] = { 'md5': md5, 'fmd5': None, 'entity': False }

        files = list_files(path)
        for file in files:
            dir, name     = os.path.split(file)
            if name == 'md5.txt':
                continue
            if not name in md5_list:
                md5_list[name] = { 'md5': None, 'fmd5': None }
            md5_list[name]['fmd5']   = get_file_md5(file)
            md5_list[name]['entity'] = True

        return md5_list

    def write_md5_txt(self, dir):
        with open(os.path.join(dir, 'md5.txt'), 'w+') as f:
            for md5 in self.md5_list:
                f.write('%s  %s\n' % (md5[1], md5[0]))

    def check_clip_exist(self, md5_lists, md5, clip, fmd5):
        for md5_list in md5_lists:
            if not clip in md5_list:
                return False
            if md5_list[clip]['entity'] and fmd5 == md5_list[clip]['fmd5']:
                return True
            if md5 == md5_list[clip]['md5']:
                return True

        return False

    def run(self):
        self.md5_list = []
        self.tmp_path = 'tmp'
        if os.path.exists(self.tmp_path):
            remove_dir(self.tmp_path)
        os.mkdir(self.tmp_path)

        if not os.path.exists(self.args.failure_path):
            os.mkdir(self.args.failure_path)

        if not os.path.exists(self.args.conformance_path):
            os.mkdir(self.args.conformance_path)

        paths = os.walk(self.args.clips)
        for path, dir_lst, file_lst in paths:
            for file in file_lst:
                file_name, file_ext = os.path.splitext(file)
                bit_name = file_name + '.bit'

                tmp_clip_path = os.path.join(self.tmp_path, file)
                os.mkdir(tmp_clip_path)
                clip = os.path.join(path, file)

                bit_path = ''
                md5_path = None
                zip_file = zipfile.ZipFile(clip)
                for name in zip_file.namelist():
                    root, extension = os.path.splitext(name)
                    if 'yuv.md5' in name and not 'first_picture.yuv.md5' in name:
                        md5_path = os.path.join(tmp_clip_path, name)
                        zip_file.extract(name, tmp_clip_path)

                    if extension == '.bit':
                        bit_path = os.path.join(tmp_clip_path, name)
                        zip_file.extract(name, tmp_clip_path)

                yuv_a = bit_path + '_a.yuv'
                yuv_b = bit_path + '_b.yuv'

                vtm_md5 = None
                if self.args.vvdec != None:
                    subprocess.run('%s -b "%s" -o "%s"' % (self.args.vvdec, bit_path, yuv_a))
                    stats = os.stat(yuv_a)
                    if stats.st_size != 0:
                        vtm_md5 = get_file_md5(yuv_a)

                if vtm_md5 == None and md5_path != None:
                    with open(md5_path, 'rb+') as f:
                        line = f.read()
                        pair = line.decode('utf-8').replace('\r', '').replace('\n', '').split(' ')
                        if len(pair) > 0:
                            vtm_md5 = pair[0].lower()

                subprocess.run('%s -strict -2 -i "%s" -noautoscale "%s"' % (self.args.ffmpeg, bit_path, yuv_b))
                ffmpeg_md5 = get_file_md5(yuv_b)

                if vtm_md5 != ffmpeg_md5:
                    print("%s: md5(%s, %s) is not match" % (bit_path, vtm_md5, ffmpeg_md5))
                    if not self.check_clip_exist(self.failed, vtm_md5, bit_name, get_file_md5(bit_path)):
                        shutil.copy(bit_path, os.path.join(self.args.failure_path, bit_name))
                else:
                    if not self.check_clip_exist(self.passed, vtm_md5, bit_name, get_file_md5(bit_path)):
                        shutil.copy(bit_path, os.path.join(self.args.conformance_path, bit_name))

                if vtm_md5 != None:
                    self.md5_list.append((bit_name, vtm_md5))

        self.write_md5_txt(self.args.failure_path)
        self.write_md5_txt(self.args.conformance_path)

if __name__ == "__main__":
    m = MD5Runner()
    m.run()
