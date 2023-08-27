import os
import re
import argparse
import datetime
import json
import math
import shutil
import ul_ffmpeg

parser = argparse.ArgumentParser()
parser.add_argument("src_dir", type=str, help="Source directroy e.g. sdcard")
parser.add_argument("dst_dir", type=str, help="Target directory e.g. 20230823")
parser.add_argument("num_games", type=int, help="Number of games")
parser.add_argument("--mode", type=str, help="{none}|nocopy")
args = parser.parse_args()

source = args.src_dir
target = args.dst_dir #'20210606'
mode = args.mode

os.makedirs(target, exist_ok=True)

metafile = os.path.join(target, 'meta.json')

# print("metafile : ", metafile)

# 全体メタ情報
meta = {}
meta['title'] = "大会名"
meta['date'] = f"{datetime.date.today().month}/{datetime.date.today().day}"
meta['venue'] = "体育館"
meta['games'] = []

pattern = ".*\.(mp4|mts)"
mtslist = [source + '/'+ f for f in os.listdir(source) if re.search(pattern, f, re.IGNORECASE)] # 大小文字無視
mtslist.sort()
mts_index = 0

for i in range(1, args.num_games+1):
    game = {}
    game['dirname'] = f"game{i}"
    game['chapters'] = []
    chapter_index = 1
    last_mtime = 0
    sum_duration = 0
    for j in range(mts_index, len(mtslist)):
        mts = mtslist[j]
        mtime = os.path.getmtime(mts)
        # 次の動画への遷移条件は、、前回の動画の終了から10分以上が経過したとする
        if last_mtime != 0 and mtime - last_mtime > 600:
            last_mtime = 0
            break
        chapter = {}
        chapter['text'] = f'{chapter_index}Q'
        chapter_index += 1
        chapter['file'] = os.path.basename(mts)
        dt = datetime.datetime.fromtimestamp(mtime)
        chapter['mtime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        duration_sec = math.ceil(ul_ffmpeg.get_length(mts))
        chapter['at'] = f'{math.floor(sum_duration/60)}m:{sum_duration%60}s'
        sum_duration += duration_sec
        td = datetime.timedelta(seconds=duration_sec)
        # chapter['duration(sec)'] = duration_sec
        chapter['duration'] = f'{math.floor(duration_sec/60)}m:{duration_sec%60}s'
        game['chapters'].append(chapter)
        last_mtime = mtime + duration_sec
        mts_index += 1

        if mode == 'nocopy':
            continue

        gamedir = os.path.join(target, game['dirname'])
        os.makedirs(gamedir, exist_ok=True)
        print(f"copying {mts} to {gamedir}")
        shutil.copy2(mts, gamedir)

    meta['games'].append(game)

print(meta)

with open(metafile, 'w', encoding='utf-8') as f:
    json.dump(meta, f, ensure_ascii=False, indent=4)
