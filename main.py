from PIL import Image
import pyzbar.pyzbar as pyzbar

im = Image.open("goodCodes.jpg")

def readCode(image):
    """
    関数の概要
    あたえられた画像データから書籍JANコードを取り出し、ISBNとdetailCodeが内包された辞書型にして返します。

    書籍JANコード は、２段のバーコードのセットで構成されています。
    一段目には、ISBNが内包されています。978から始まる整数の列です。
    二段目には、図書分類コードおよび、図書本体価格が内包されています（便宜上、"detailCode"と表記します）。192から始まる整数の列です。
    接頭辞である978と192を用いて、ISBNとdetailCodeを見分けています。
    """
    
    # 画像データからバーコードを読み込みます
    pre_bcodes = pyzbar.decode(image)

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

print(readCode(im))