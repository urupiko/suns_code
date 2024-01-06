import argparse
import os
import re
import ul_ffmpeg

parser = argparse.ArgumentParser()
parser.add_argument("src_dir", type=str, help="Source directroy e.g. sdcard")
parser.add_argument("dst_dir", type=str, help="Target directory e.g. game1")
args = parser.parse_args()

source = args.src_dir
target = args.dst_dir

os.makedirs(target, exist_ok=True)

pattern = ".*\.(mp4|mov|mts)"

videolist = [source + '/' + f for f in os.listdir(source) if re.search(pattern, f, re.IGNORECASE)]  # 大小文字無視
videolist.sort()

flip_target_list = ["IMG_3488.MOV"]

for video in videolist:
    if os.path.basename(video) in flip_target_list:
        ul_ffmpeg.vflip_video(video,
                              target+'/'+os.path.splitext(os.path.basename(video))[0]+'.mp4')
    else:
        print(os.path.basename(video))
        ul_ffmpeg.reencode_video(video,
                                 target + '/' + os.path.splitext(os.path.basename(video))[0]+'.mp4')
