from PIL import Image
from pdf2image import convert_from_path
import tempfile
import pyzbar.pyzbar as pyzbar
import os



def readCode(pdf: str, page_num: int) -> dict:
    """
    指定されたpathにあるpdfファイル（引数: pdf）の、指定された一つのページ（引数: page_num）から、
    書籍JANコードを取り出し、ISBNとdetailCodeが内包された辞書型（{ISBN: , detailCode:}）にして返します。
    
    書籍JANコード は、２つのバーコードのセットで構成されています。
    一段目には、ISBNが内包されています。978から始まる整数の列です。
    二段目には、図書分類コードおよび、図書本体価格が内包されています（便宜上、"detailCode"と表記します）。192から始まる整数の列です。
    接頭辞である978と192を用いて、ISBNとdetailCodeを見分けています。
    """

    # 指定されたpdfページの画像ファイルを作成します
    im = convert_from_path(pdf, first_page=page_num, last_page=page_num)
    # 指定されたページの画像は、一時的なファイルとして保存されます
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_f:
        im[0].save(temp_f.name, format="PNG")
        temp_file_path = temp_f.name
        
    # 一時的な画像ファイルからバーコードを読み込みます
    try:
        with Image.open(temp_file_path) as img:
            pre_bcodes = pyzbar.decode(img)
    # バーコードを読み込んだら、一時的なファイルを削除します
    finally:
        os.remove(temp_file_path)

    # 画像データ内に、書籍JANコードがあるか調べます
    # まずは、数で判定します
    if len(pre_bcodes) == 0:
        raise ValueError("ページ内にバーコードがありません")
    elif len(pre_bcodes) == 1 or len(pre_bcodes) >= 3:
        raise ValueError("バーコードの数が不正です")

    # バーコードが２つあったらJANコードの振り分けをします
    bookJAN = {}
    for i in pre_bcodes:
        if str(int(i.data))[:3] == "978":
            bookJAN["ISBN"] = int(i.data)
        elif str(int(i.data))[:3] == "192":
            bookJAN["detailCode"] = int(i.data)
        else:
            raise ValueError("バーコードの値が不正です")

    return bookJAN



if __name__ == "__main__":
    pf = "test-comic.pdf"
    print(readCode(pf, 3))