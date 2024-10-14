from PIL import Image
from pdf2image import convert_from_path
import tempfile
import pyzbar.pyzbar as pyzbar
import os

pd = "test-comic.pdf"

def readCode(pdf: str, whereIs: int) -> dict:
    """
    関数の概要
    あたえられたpathにあるpdfから、書籍JANコードを取り出し、ISBNとdetailCodeが内包された辞書型にして返します。
    注意点として、指定された1つのページから書籍JANコードを読み込むので、事前に、どのページに書籍JANコードがあるか知っておく必要があります。

    書籍JANコード は、２段のバーコードのセットで構成されています。
    一段目には、ISBNが内包されています。978から始まる整数の列です。
    二段目には、図書分類コードおよび、図書本体価格が内包されています（便宜上、"detailCode"と表記します）。192から始まる整数の列です。
    
    接頭辞である978と192を用いて、ISBNとdetailCodeを見分けています。
    """

    # 指定されたページ（書籍JANコードがあるとされているページ）の画像データを作成します。
    im = convert_from_path(pdf, first_page=whereIs, last_page=whereIs)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_f:
        im[0].save(temp_f.name, format="PNG")
        temp_file_path = temp_f.name
        
    # 画像データからバーコードを読み込みます
    try:
        with Image.open(temp_file_path) as im:
            pre_bcodes = pyzbar.decode(im)
    finally:
        os.remove(temp_file_path)
    return pre_bcodes

print(readCode(pd, 3))