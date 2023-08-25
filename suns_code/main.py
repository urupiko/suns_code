import re
import os
import errno
import json
import subprocess
import argparse
import datetime
import platform
import tempfile
import sys

import ul_thumbnail
import ul_youtube

os_dir = 'win' if platform.system() == 'Windows' else 'mac'
ffmpeg_dir = f"ffmpeg/{os_dir}/"

def get_length(filename):
    result = subprocess.run([ffmpeg_dir + "ffprobe", "-v", "quiet", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
                             capture_output=True, text=True
        )
    return float(result.stdout)

def add_telop(filepath, text):
    root_ext_pair = os.path.splitext(filepath)
    new_file = root_ext_pair[0] + '_telop' + ".mp4" # root_ext_pair[1]
    font_file = 'C\:/WINDOWS/Fonts/YuGothR.ttc' if platform.system() == 'Windows' else '/System/Library/Fonts/ヒラキノ角コシック W8.ttc'

    with tempfile.TemporaryDirectory() as tmpdir:
        # tmpdir にmp4を作る
        tmp_mp4 = os.path.join(tmpdir, 'tmp.mp4')
        subprocess.run([ffmpeg_dir + 'ffmpeg', '-i', f'{filepath}', '-c', 'copy', f'{tmp_mp4}'])
        # 前半5秒とその他に分割する
        subprocess.run([ffmpeg_dir + 'ffmpeg', '-i', f'{tmp_mp4}',
                        '-c', 'copy', '-f', 'segment', '-segment_times', '5',
                        os.path.join(tmpdir, '%03d.mp4')])
        # 前半5秒にテロップを入れる
        # Powered by：http://ffmpeg.shanewhite.co/
        # -filter_complex "[0:v]drawtext=fontfile='{}':text='{}':fontsize=80:fontcolor=ffffff:alpha='if(lt(t,0),0,if(lt(t,1),(t-0)/1,if(lt(t,4),1,if(lt(t,5),(1-(t-4))/1,0))))':x=100:y=(h-text_h) -100" \
        command_args = """
        {} -y -i {} \
        -filter_complex "[0:v]drawtext=fontfile='{}':text='{}':fontsize=80:fontcolor=ffffff:alpha='if(lt(t,0),0,if(lt(t,0),(t-0)/0,if(lt(t,4),1,if(lt(t,5),(1-(t-4))/1,0))))':x=100:y=(h-text_h) -100" \
        -vb 16000k \
        -x264opts "interlaced=1:tff=1" \
        -video_track_timescale 30k \
        -map 0:a -c:a copy \
        {}
        """.format(
            ffmpeg_dir + 'ffmpeg', os.path.join(tmpdir, '000.mp4'),
            font_file, text,
            os.path.join(tmpdir, '000_telop.mp4')
            ).replace('\n', '')
        result = subprocess.check_output(command_args, shell=True)
        # くっつける
        f0 = os.path.join(tmpdir, '000_telop.mp4')
        # f0 = os.path.join(tmpdir, '000.mp4')
        f1 = os.path.join(tmpdir, '001.mp4')
        listfile_path = os.path.join(tmpdir, 'list.txt')
        with open(listfile_path, 'w', encoding='utf-8' ) as f:
            f.write('file ' + f0 + '\n')
            f.write('file ' + f1)

        command_args = """
        {} -y -fflags +discardcorrupt -f concat -safe 0 -i {} \
        -c copy \
        {}
        """.format(ffmpeg_dir + 'ffmpeg', listfile_path,  new_file).replace('\n', '')
        result = subprocess.check_output(command_args, shell=True)
        print(result)

    return new_file

parser = argparse.ArgumentParser()
parser.add_argument("src_dir", type=str, help="Source directroy e.g. 20210606")
parser.add_argument("mode", type=str, help="create_thumbnail/upload_thumbnail/mkdir/conv/upload")
args = parser.parse_args()

target = args.src_dir #'20210606'
mode = args.mode
if not os.path.isdir(target):
    raise FileNotFoundError (errno.ENOENT, os.strerror(errno.ENOENT), target)
basedir = os.path.join(os.getcwd(), target)
metafile = os.path.join(basedir, 'meta.json')
chapterfile = os.path.join(basedir, 'chapter.txt')

print('getcwd   : ', os.getcwd())
print("__file__ : ", __file__)
print("metafile : ", metafile)

with open(metafile, encoding='utf-8') as f:
    meta = json.load(f)

if mode == 'mkdir':
    for game in meta['games']:
        if 'enabled' in game:
            if game['enabled'] is False:
                continue
        os.makedirs(os.path.join(basedir, game['dirname']), exist_ok=True)
        print(game['dirname'] + ' is created')
    sys.exit(0)

if mode == 'create_thumbnail':
    for game in meta['games']:
        if 'enabled' in game:
            if game['enabled'] is False:
                continue
        ul_thumbnail.create_thumbnail(os.path.join(basedir, game['dirname']))
    sys.exit(0)

if mode == 'upload_thumbnail':
    for game in meta['games']:
        if 'enabled' in game:
            if game['enabled'] is False:
                continue
        ul_youtube.upload_thumbnail(os.path.join(basedir, game['dirname']))
    sys.exit(0)

for game in meta['games']:
    if 'enabled' in game:
        if game['enabled'] is False:
            continue

    segment = 1
    sum_duration = 0.0
    gamedir = os.path.join(basedir, game['dirname'])
    info = {}
    info['opponent'] = game['opponent']

    # 連結対象動画ファイルリスト作成
    listfile_path = os.path.join(gamedir, 'mtslist.txt').replace(os.path.sep, '/')
    pattern = ".*\.(mp4|mts)"
    mtslist = [gamedir + '/'+ f for f in os.listdir(gamedir) if re.search(pattern, f, re.IGNORECASE)] # 大小文字無視
    mtslist.sort()

    # chapter情報固有処理
    chapter_dict = {}
    if 'chapters' in game :
        for chapter in game['chapters']:
            original_mts = gamedir+'/'+chapter['file']
            # [封印!] テロップ追加動画を作成する => テロップは作れたが、無圧縮で連結ができないので諦める。やるなら全部エンコード
            # telopped_mts = add_telop(original_mts, chapter['text'])
            # mtslist = [s.replace(original_mts,telopped_mts) for s in mtslist]
            # chapter_dict[telopped_mts] = chapter['text']
            chapter_dict[chapter['file']] = chapter['text']

    with open(listfile_path, 'w', encoding='utf-8' ) as f:
        mtss = list(map(lambda mts:'file '+mts.replace(os.path.sep, '/'), mtslist))
        f.write("\n".join(mtss))
 
    title = meta['date'] + ' ' + meta['title'] + ' ' + game['opponent']
    # description 作成
    desc_list = []
    for mts in mtslist:
       duration = get_length(mts)
       sec = int(sum_duration)
       td = datetime.timedelta(seconds=sec)
       sum_duration += duration
       # チャプターが指定されていた場合は指定ファイルだけdesc_listに書き込む
       if 'chapters' in game :
         if os.path.basename(mts) in chapter_dict:
            desc_list.append(str(int(td.seconds/60)) + ":" + str(td.seconds%60).zfill(2) + " " + chapter_dict[os.path.basename(mts)])
         else:
           continue 
       else:
         desc_list.append(str(int(td.seconds/60)) + ":" + str(td.seconds%60).zfill(2) + " " + str(segment) + "Q")
       segment += 1
    description = ''
    if 'score' in game :
        description += game['friend'] + ' ' + game['score'] + ' ' + game['opponent'] + '\n'
        info['score'] = game['score']
    if 'venue' in meta :
        description += '@' + meta['venue'] + '\n'
    description += '\n'.join(desc_list)
    print(description)

    outfile_path = os.path.join(basedir, game['dirname']+'.mp4')
    # outfile_path = os.path.join(basedir, game['dirname']+'.mts')
    if mode == 'conv':
        subprocess.run([ffmpeg_dir + 'ffmpeg', '-fflags', '+discardcorrupt', '-y',  '-f', 'concat', '-safe', '0', '-i', f'{listfile_path}', '-c', 'copy', f'{outfile_path}'])

    # [封印!] テロップの動画の削除
    # for key in chapter_dict:
    #     os.remove(key)

    with open(chapterfile, 'a', encoding='utf-8') as f:
        f.write(f'title: {title}' + '\n' + f'{str(description)[0:]}' + '\n')

    # Youtube にアップロード
    # Required: httplib2, apiclient, google-api-python-client, oauth2client
    if mode == 'upload':
        options = dict(
            file = outfile_path,
            title = title,
            description = description,
            category = 17,
            privacyStatus = 'unlisted'
        )
        video_id = ul_youtube.upload_video(options)
        if video_id is not None:
            info['video_id'] = video_id

    infofile_path = os.path.join(gamedir, 'info.json').replace(os.path.sep, '/')
    with open(infofile_path, 'w', encoding='utf-8' ) as f:
        json.dump(info, f, ensure_ascii=False, indent=4, sort_keys=True)
