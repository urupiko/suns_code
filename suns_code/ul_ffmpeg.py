import os
import re
import subprocess
import platform
import tempfile
import datetime

os_dir = 'win' if platform.system() == 'Windows' else 'mac'
ffmpeg_dir = f"ffmpeg/{os_dir}/"


def get_length(filename):
    result = subprocess.run([ffmpeg_dir + "ffprobe", "-v", "quiet", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
                            capture_output=True, text=True
                            )
    return float(result.stdout)


def concat_video(game, gamedir, outfile_path):
    segment = 1
    sum_duration = 0.0

    # 連結対象動画ファイルリスト作成
    listfile_path = os.path.join(gamedir, 'mtslist.txt').replace(os.path.sep, '/')
    pattern = ".*\.(mp4|mts|mov)"
    mtslist = [gamedir + '/' + f for f in os.listdir(gamedir) if re.search(pattern, f, re.IGNORECASE)]  # 大小文字無視
    mtslist.sort()

    # chapter情報固有処理
    chapter_dict = {}
    if 'chapters' in game:
        for chapter in game['chapters']:
            # [封印!] テロップ追加動画を作成する => テロップは作れたが、無圧縮で連結ができないので諦める。やるなら全部エンコード
            # original_mts = gamedir+'/'+chapter['file']
            # telopped_mts = add_telop(original_mts, chapter['text'])
            # mtslist = [s.replace(original_mts,telopped_mts) for s in mtslist]
            # chapter_dict[telopped_mts] = chapter['text']

            # キーチャプター指定時のみチャプター対象辞書に追加
            if chapter.get('is_key') is True:
                chapter_dict[chapter['file']] = chapter['text']

    with open(listfile_path, 'w', encoding='utf-8') as f:
        mtss = list(map(lambda mts: 'file '+mts.replace(os.path.sep, '/'), mtslist))
        f.write("\n".join(mtss))

    # description 作成
    desc_list = []
    for mts in mtslist:
        duration = get_length(mts)
        sec = int(sum_duration)
        td = datetime.timedelta(seconds=sec)
        sum_duration += duration
        # チャプターが指定されていた場合は指定ファイルだけdesc_listに書き込む
        if 'chapters' in game:
            if os.path.basename(mts) in chapter_dict:
                desc_list.append(str(int(td.seconds/60)) + ":" + str(td.seconds % 60).zfill(2) + " " + chapter_dict[os.path.basename(mts)])
            else:
                continue
        else:
            desc_list.append(str(int(td.seconds/60)) + ":" + str(td.seconds % 60).zfill(2) + " " + str(segment) + "Q")
        segment += 1

    # outfile_path = os.path.join(basedir, game['dirname']+'.mts')
    subprocess.run([ffmpeg_dir + 'ffmpeg', '-fflags', '+discardcorrupt', '-y',  '-f', 'concat', '-safe', '0', '-i', f'{listfile_path}', '-c', 'copy', f'{outfile_path}'])

    # [封印!] テロップの動画の削除
    # for key in chapter_dict:
    #     os.remove(key)

    return desc_list


def add_telop(filepath, text):
    root_ext_pair = os.path.splitext(filepath)
    new_file = root_ext_pair[0] + '_telop' + ".mp4"  # root_ext_pair[1]
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
        with open(listfile_path, 'w', encoding='utf-8') as f:
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


def vflip_video(source_path, target_path):
    subprocess.run([ffmpeg_dir + 'ffmpeg', '-i', f'{source_path}', '-crf', '21', '-vf', 'vflip',  f'{target_path}'])
    pass


def reencode_video(source_path, target_path):
    subprocess.run([ffmpeg_dir + 'ffmpeg', '-i', f'{source_path}', '-crf', '21', '-r', '29.97',  f'{target_path}'])
    pass
