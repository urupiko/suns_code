import os
import errno
import json
import argparse

import ul_thumbnail
import ul_youtube
import ul_ffmpeg

parser = argparse.ArgumentParser()
parser.add_argument("target_dir", type=str, help="Target directroy e.g. 20210606")
parser.add_argument("mode", type=str, help="create_thumbnail/upload_thumbnail/conv/upload")
args = parser.parse_args()

target = args.target_dir  # '20210606'
mode = args.mode
if not os.path.isdir(target):
    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), target)
basedir = os.path.join(os.getcwd(), target)
metafile = os.path.join(basedir, 'meta.json')

print("metafile : ", metafile)

with open(metafile, encoding='utf-8') as f:
    meta = json.load(f)

for game in meta['games']:
    if 'enabled' in game:
        if game['enabled'] is False:
            continue

    gamedir = os.path.join(basedir, game['dirname'])
    chapterfile = os.path.join(gamedir, 'chapter.txt')

    outfile_path = os.path.join(basedir, game['dirname']+'.mp4')
    title = meta['date'] + ' ' + meta['title'] + ' ' + game['opponent']
    description = ''

    if mode == 'conv':
        desc_list = ul_ffmpeg.concat_video(game,
                                           gamedir,
                                           outfile_path)
        if 'score' in game:
            description += game['friend'] + ' ' + game['score'] + ' ' + game['opponent'] + '\n'
        if 'venue' in meta:
            description += '@' + meta['venue'] + '\n'
        description += '\n'.join(desc_list)
        print(description)
        with open(chapterfile, 'w', encoding='utf-8') as f:
            f.write(f'{str(description)[0:]}' + '\n')

    if mode == 'upload':
        if not os.path.isfile(chapterfile):
            continue
        with open(chapterfile, 'r', encoding='UTF-8') as f:
            description = f.read()
        options = dict(
            file=outfile_path,
            title=title,
            description=description,
            category=17,  # sports
            privacyStatus='unlisted'
        )
        video_id = ul_youtube.upload_video(options)

        info = {}
        info['opponent'] = game['opponent']
        if 'score' in game:
            info['score'] = game['score']
        if video_id is not None:
            info['video_id'] = video_id
        infofile_path = os.path.join(gamedir, 'info.json').replace(os.path.sep, '/')
        with open(infofile_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=4, sort_keys=True)

    if mode == 'create_thumbnail':
        ul_thumbnail.create_thumbnail(gamedir)

    if mode == 'upload_thumbnail':
        ul_youtube.upload_thumbnail(gamedir)
