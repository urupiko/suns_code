import os
import re
import argparse
import datetime
import json
import math
import shutil
import config
import ul_ffmpeg
import logging

# logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("src_dir", type=str, help="Source directroy e.g. sdcard")
parser.add_argument("dst_dir", type=str, help="Target directory e.g. 20230823")
parser.add_argument("--mode", type=str, help="{none}|nocopy")
args = parser.parse_args()

source = args.src_dir
target = args.dst_dir  # '20210606'
mode = args.mode

os.makedirs(target, exist_ok=True)

metafile = os.path.join(target, 'meta.json')
logging.info("metafile : " + metafile)

# 全体メタ情報
meta = {}
meta['title'] = "大会名"
meta['date'] = f"{datetime.date.today().year}/{datetime.date.today().month}/{datetime.date.today().day}"
meta['venue'] = "体育館"
meta['games'] = []

pattern = ".*\.(mp4|mts|mov)"
mtslist = [source + '/' + f for f in os.listdir(source) if re.search(pattern, f, re.IGNORECASE)]  # 大小文字無視
mtslist.sort()
mts_index = 0

for i in range(1, len(mtslist)):
    game = {}
    game['enabled'] = True
    game['dirname'] = f"game{i}"
    game['friend'] = config.FRIEND_TEAM_NAME
    game['opponent'] = "対戦チーム名"
    game['score'] = "0-0"
    game['chapters'] = []
    chapter_index = 1
    last_mtime = 0
    sum_duration = 0
    for j in range(mts_index, len(mtslist)):
        # mts       1.....2.....3.....4
        # mtime          *     *     *
        # duration  xxxxxx
        mts = mtslist[j]
        mtime = os.path.getmtime(mts)
        duration_sec = math.ceil(ul_ffmpeg.get_length(mts))
        elapsed_sec = (mtime-duration_sec) - last_mtime
        # 次の動画への遷移条件は、前回の動画の終了時(last_mtime)から10分以上が経過したとする
        if last_mtime != 0 and elapsed_sec > 600:
            print(f"go to next. elapsed: {elapsed_sec/60} [min]")
            last_mtime = 0
            break

        # チャプター情報を記録
        chapter = {}
        dt = datetime.datetime.fromtimestamp(mtime)
        chapter['is_key'] = True
        chapter['text'] = f'{chapter_index}Q'
        chapter['at'] = f'{math.floor(sum_duration/60)}m:{sum_duration%60}s'
        sum_duration += duration_sec
        chapter['duration'] = f'{math.floor(duration_sec/60)}m:{duration_sec%60}s'
        chapter['mtime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        chapter_index += 1
        chapter['file'] = os.path.basename(mts)
        game['chapters'].append(chapter)
        last_mtime = mtime
        mts_index += 1
        logging.info(chapter['file'] + ' ' + chapter['mtime'] + ' ' + datetime.datetime.fromtimestamp(last_mtime).strftime('%Y-%m-%d %H:%M:%S'))

        if mode == 'nocopy':
            continue

        # コピー処理を実行
        gamedir = os.path.join(target, game['dirname'])
        os.makedirs(gamedir, exist_ok=True)
        print(f"copying {mts} to {gamedir}")
        shutil.copy2(mts, gamedir)
    
    meta['games'].append(game)
    if mts_index == len(mtslist):
        break

print(meta)

with open(metafile, 'w', encoding='utf-8') as f:
    json.dump(meta, f, ensure_ascii=False, indent=4)
