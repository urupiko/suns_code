import os
import re
import argparse
import errno
import json
import shutil
import platform

from PIL import Image, ImageDraw, ImageFont

dirname = os.path.dirname
FONT_PATH = os.path.join(dirname(dirname(__file__)), 'font/Let_s_go_Digital_Regular.ttf')
FONT_SIZE = 100
# FONT_COLOR = '#ffffff'
FONT_COLOR = '#ffd700'
OFFSET_X = 140
OFFSET_Y = 160
IMAGE_WIDTH=1280
IMAGE_HEIGHT=720

def pillar_box(photo: Image):
    new_width = photo.width * IMAGE_HEIGHT // photo.height 
    new_image = Image.new('RGBA', (IMAGE_WIDTH, IMAGE_HEIGHT), (0,0,0))
    offset = (IMAGE_WIDTH - new_width)//2 
    new_image.paste(photo.resize((new_width,IMAGE_HEIGHT)), (offset,0))
    return new_image

# [API仕様]
# 引数: 画像加工したいディレクトリパス
# 返値: なし
def create_thumbnail(target):
    thumbnail_path = os.path.join(target, 'thumbnail.jpg')
    if os.path.isfile(thumbnail_path):
        os.remove(thumbnail_path)

    info_path = os.path.join(target, 'info.json')
    if not os.path.isfile(info_path):
        print('skipped: not found '+ info_path)
        return
    with open(info_path, encoding='utf-8') as f:
        info = json.load(f)
    
    # 最初に見つかったjpgファイルを対象ファイルとする
    src_path = [os.path.join(target, f) for f in os.listdir(target) 
                if re.search(".*\.(jpg|jpeg)", f, re.IGNORECASE)][0]
    dst_path = thumbnail_path

    # スコアが存在しない場合は、コピーして終了
    if not 'score' in info:
        shutil.copy2(src_path, dst_path)
        print('copied: ' + dst_path)
        return

    # 描画開始
    draw_image = Image.new('RGBA',(IMAGE_WIDTH, IMAGE_HEIGHT))
    draw = ImageDraw.Draw(draw_image)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # 画像ファイル
    photo_image = Image.open(src_path).convert('RGBA')
    ratio_a = IMAGE_WIDTH/IMAGE_HEIGHT
    ratio_b = photo_image.width/photo_image.height
    if photo_image.width < IMAGE_WIDTH or photo_image.height < IMAGE_HEIGHT:
        raise NotImplementedError()
    if ratio_a == ratio_b:  
        # アスペクト比が同一ならリサイズのみ
        photo_image = photo_image.resize((IMAGE_WIDTH,IMAGE_HEIGHT))
    elif ratio_a > ratio_b:
        # 逆レターボックス
        photo_image = pillar_box(photo_image)
    else:
        # レターボックス
        raise NotImplementedError()

    ## ボックス
    bbox = draw.textbbox((OFFSET_X, IMAGE_HEIGHT- OFFSET_Y),
                         info['score'], 
                         font=font, 
                         spacing=4,
                         align='left',
                         anchor='lt')
    draw.rectangle(
        [bbox[0]-20, bbox[1]-20, bbox[2]+20, bbox[3]+20],
        fill = (0, 0, 0, 150)
    )
    # draw.rounded_rectangle(
    #   radius=20,

    # テキスト
    draw.text((OFFSET_X, IMAGE_HEIGHT-OFFSET_Y),    # 座標
            info['score'],            # 描画するテキストタイトル
            FONT_COLOR,
            font=font,       # フォント設定
            spacing=4,       # テキスト間隔にとるスペース
            align='left',    # テキストの揃え方（center:中央揃え, left:左揃え, right:右揃え）
            anchor='lt'      # アンカーテキスト
            )

    # 合成
    output_image = Image.alpha_composite(photo_image, draw_image)
    output_image = output_image.convert('RGB')
    output_image.save(dst_path, quality = 100)

    print('created: ' + dst_path)

# テストコード
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_dir", type=str, help="Target directroy e.g. 20210606/game1")
    args = parser.parse_args()
    target = args.target_dir
    if not os.path.isdir(target):
        raise FileNotFoundError (errno.ENOENT, os.strerror(errno.ENOENT), target)

    create_thumbnail(target)