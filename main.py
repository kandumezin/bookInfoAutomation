from PIL import Image
from pdf2image import convert_from_path
import tempfile
import pyzbar.pyzbar as pyzbar
import os
import requests
import xml.etree.ElementTree as ET
import pandas as pd


def readCode(pdf: str, page_num: int) -> dict:
    """
    指定されたpathにあるpdfファイルの、指定された一つのページ（引数: page_num）から、
    書籍JANコードを取り出し、ISBNとdetailCodeが内包された辞書型（{ISBN: , detailedCode:}）にして返します。
    
    Args:
        pdf (str): PDFファイルへのパス。
        page_num (int): 抽出対象のページ番号。

    Returns:
        dict: ISBNと詳細コードを格納した辞書。フォーマットは以下の通り:
            {
                "ISBN": str,         # ISBNコード
                "detailedCode": str   # 図書分類コードおよび図書本体価格を含むコード
            }

            
    書籍JANコード は、２つのバーコードのセットで構成されています。
    一段目には、ISBNが内包されています。978から始まる整数の列です。
    二段目には、図書分類コードおよび、図書本体価格が内包されています（便宜上、"detailedCode"と表記します）。192から始まる整数の列です。
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
            bookJAN["ISBN"] = str(int(i.data))
        elif str(int(i.data))[:3] == "192":
            bookJAN["detailedCode"] = str(int(i.data))
        else:
            raise ValueError("バーコードの値が不正です")

    return bookJAN


def getInfo(ISBN: str) -> dict:
    """
    ISBN(str)から本の情報(dict)を取得します。
    国立国会図書館が提供する、「外部提供インターフェース」の「OpenSearch」をもちいて、取得しています。

    Args:
        ISBN(str):本のISBN

    Returns:
        bookInfo(dict):本の情報が詰まった辞書

    """
    # 国立国会図書館OpenSearchのエンドポイントURLと、与えられたISBNをもちいて、
    # HTTPリクエストの クエリ付き URL を作成します
    endPointUrl = "https://ndlsearch.ndl.go.jp/api/opensearch?isbn="
    url = endPointUrl + str(ISBN)

    # リクエストします。XMLデータ が帰ってきます
    try:
        res = requests.get(url)
    except Exception as e:
        print(e)
        exit()

    # 帰ってきた XMLデータ を、dict に変換します。
    root = ET.fromstring(res.text)
    xml_bookInfo = root.find(".//item")
    bookInfo = {}
    for i in xml_bookInfo:
        bookInfo[f"{i.tag}"] = i.text
    
    return bookInfo


def addDatabase(bookInfo: dict) -> None:
    """
    本の情報(dict)を、データベースに格納します。
    データベースがなかったなら、新しく作成（ファイル名:"bookInfoAutomation.csv"）されます

    Args:
        bookInfo(dict): 本の情報が詰まった辞書

    return:
        None
    """
    # データベースがあるかないか調べます。なかったら新規作成して、本のデータを格納します。
    if not os.path.isfile("bookInfoAutomation.csv"):
        df = pd.DataFrame(bookInfo, index=[0])
        df.to_csv("bookInfoAutomation.csv", encoding="UTF-8")
    else:
        df = pd.read_csv("bookInfoAutomation.csv")
        add_df = pd.DataFrame(bookInfo, index=[0])
        df = pd.concat([df, add_df])
        print(df)
        df.to_csv("bookInfoAutomation.csv", encoding="UTF-8")

    




"""
if __name__ == "__main__":
    pf = "test-comic.pdf"
    bookJAN = readCode(pf, 3)
    ISBN, detailedCode = bookJAN["ISBN"], bookJAN["detailedCode"]
    getInfo(ISBN)
"""

if __name__ == "__main__":
    bookInfo = getInfo("9784063600568")
    print(bookInfo)
    addDatabase(bookInfo)