from pdf2image import convert_from_path
from PIL import Image
import tempfile
import os

# PDFファイルのパスを指定
pdf_path = 'example.pdf'

# PDFの1ページ目を画像に変換
images = convert_from_path(pdf_path, first_page=1, last_page=1)

# 一時ファイルに画像を保存
with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
    # 画像データを一時ファイルに保存
    images[0].save(temp_file.name, format='PNG')
    
    # 一時ファイルのパスを取得
    temp_file_path = temp_file.name

# 一時ファイルを利用する
try:
    # 一時ファイルを開いて、画像を表示する（または他の処理を行う）
    with Image.open(temp_file_path) as img:
        img.show()  # 画像を表示
finally:
    # 一時ファイルを削除
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
        print(f"一時ファイル '{temp_file_path}' を削除しました。")

# PDFファイルのパスを指定
pdf_path = 'example.pdf'

# 変換したいページの範囲を指定
first_page = 1  # 開始ページ（1から始まる）
last_page = 3   # 終了ページ

# PDFの指定したページを画像に変換
images = convert_from_path(pdf_path, first_page=first_page, last_page=last_page)

# 変換されたページの画像を保存
for i, image in enumerate(images):
    image.save(f'page_{first_page + i}.png', 'PNG')