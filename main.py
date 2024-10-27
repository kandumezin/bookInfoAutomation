# 組み込みモジュール
import re
from typing import Literal, Union
import tempfile
import os
import shutil
import xml.etree.ElementTree as ET
# 外部モジュール
from PIL import Image
import pyzbar.pyzbar as pyzbar
import requests
import pandas as pd
import pymupdf



def readCode(pdfPath: str, numberOfPages: int, startingPoint: Literal["end", "first"]) -> Union[dict, str]:
    """
    指定されたpathにあるpdfファイルの、指定されたページ範囲から、書籍JANコードを探して読み取ります。
    そして、書籍JANコードをISBNとdetailCodeが内包された辞書型にして返します。
    もしも、PDFファイル中に書籍JANコードがなかったのなら、そのPDFファイルの Path を返します。
    Args:
        pdf(str): PDFファイルへのパス
        numberOfPages(int): どれくらいの量のページから書籍JANコードを探すか指定します。
        startingPoint("end" or "first"):
            "end": 後ろのページから書籍JANコードを探します
            "first": 先頭のページから書籍JANコードを探します

    Returns:

        dict: ISBNと詳細コードを格納した辞書。フォーマットは以下の通り:
            {
                "ISBN": str,         # ISBNコード
                "detailedCode": str   # 図書分類コードおよび図書本体価格を含むコード
            }
    Raises:
        ValueError("{pdfPath}は、PDFではありません")
            与えられたファイルが、PDF ではないときに表示されます。
        ValueError("範囲内に有効なバーコードが見つかりませんでした。")

    Notes: 
        書籍JANコード は、２つのバーコードのセットで構成されています。
        一段目には、ISBNが内包されています。978から始まる整数の列です。
        二段目には、図書分類コードおよび、図書本体価格が内包されています（便宜上、"detailedCode"と表記します）。192から始まる整数の列です。
        接頭辞である978と192を用いて、ISBNとdetailCodeを見分けています。
    """
    # 与えられた　Path から、PDF を読み込みます。
    if os.path.splitext(pdfPath)(1) != ".pdf":
        raise ValueError(f"{os.path.basename(pdfPath)} は、PDF ではありません。")
    doc = pymupdf.Document(pdfPath)

    # 指定されたページ数と、ページ数を数え始める場所から、読み取るページ範囲を作成します。
    # 後ろからページ数を数え、指定されたページ数分のページ範囲を作成
    if startingPoint == "end":
        numberOfPages = -1 * numberOfPages
        pageRange = range(numberOfPages,0)
    # 前からページ数を数え、指定されたページ数分のページ範囲を作成
    elif startingPoint == "first":
        pageRange = range(0, numberOfPages)
    # ページ範囲が適切か確認します。
    if len(pageRange) > doc.page_count:
            raise ValueError(f"読み込もうとしているページ数が、PDF の全ページ数を超えています。 読み込もうとしているページ数:{len(pageRange)} > PDF の全ページ数:{doc.page_count}")

    # 指定されたページ範囲から、書籍JANコードを探します。
    # 指定されたページ範囲について、それぞれのページを画像に変換します。その画像からバーコードを読み取ります。
    for i in pageRange:
        with tempfile.NamedTemporaryFile(suffix=".png") as temp_f:
            zoom_x = 2.0  # horizontal zoom
            zoom_y = 2.0  # vertical zoom
            mat = pymupdf.Matrix(zoom_x, zoom_y)
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat)
            pix.save(temp_f.name)
            with Image.open(temp_f.name) as temp_pic:
                bcodes = pyzbar.decode(temp_pic, symbols=[pyzbar.ZBarSymbol.EAN13])
        # 書籍JANコードは、2つのバーコードで構成されているので、バーコードが二つあるか判定します。
        if len(bcodes) <= 1 or len(bcodes) >= 3:
            continue
        
        # バーコードが２つあったらJANコードの振り分けをします
        bookJAN = {}
        for i in bcodes:
            if (str(int(i.data)).startswith("978", "979")):
                bookJAN["ISBN"] = str(int(i.data))
            elif str(int(i.data)).startswith("192"):
                bookJAN["detailedCode"] = str(int(i.data))
            else:
                pass
        if bool(bookJAN):
            break

    # もし、指定されたページ範囲から書籍JANコードを見つけられなかった場合、そのPDFのpathを返します。
    return bookJAN if bookJAN else pdfPath


def getInfo(ISBN: str) -> dict:
    """
    ISBN(str)から本の情報(dict)を取得します。
    国立国会図書館が提供する、「外部提供インターフェース」の「OpenSearch」をもちいて、取得しています。
    Args:
        ISBN(str):本のISBN
    Returns:
        bookInfo(dict):本の情報が詰まった辞書
    Raises:
        ValueError("国立国会図書館で、指定された ISBN をもつ書籍情報を見つけられませんでした。")
    """
    if not (str(int(i.data)).startswith("978", "979")):
        raise ValueError(f"あたえられた値が ISBN ではありません。あたえられた値: {ISBN}")

    
    # 国立国会図書館OpenSearchのエンドポイントURLと、与えられたISBNをもちいて、
    # HTTPリクエストの クエリ付き URL を作成します
    endPointUrl = "https://ndlsearch.ndl.go.jp/api/opensearch?isbn="
    url = endPointUrl + str(ISBN)
    # リクエストします。XMLデータ が帰ってきます。帰ってこなかったら、Error を出します。
    try:
        res = requests.get(url)
    except Exception as e:
        print(e)
        exit()
    if not bool(res).text:
        raise ValueError("国立国会図書館から、指定された ISBN をもつ書籍情報を見つけられませんでした。")
    

    # 帰ってきた XMLデータ の中から、書籍情報を取り出して、dict に変換します。
    root = ET.fromstring(res.text)
    xml_bookInfo = root.find(".//item")
    if not bool(xml_bookInfo):
        raise ValueError("国会図書館から帰ってきた XMLデータ の型が不正です。もしかしたら仕様変更があったのかもしれません")
    bookInfo = {}
    bookInfo["ISBN"] = ISBN
    for i in xml_bookInfo:
        bookInfo[f"{i.tag + str(i.attrib)}"] = i.text

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
    # データベースがあるかないか調べます。なかったら新規作成します
    if not os.path.isfile("bookInfoAutomation.csv"):
        df = pd.DataFrame(columns=bookInfo.keys())
        df.to_csv("bookInfoAutomation.csv", encoding="UTF-8")
    
    # データベースを読み込んで、同一の ISBN をもつ行があるか検索します。そしてあった（重複）なら、データを追加しません
    df = pd.read_csv("bookInfoAutomation.csv", index_col=0)
    result = (df['ISBN'] == int(bookInfo["ISBN"]))
    if result.sum().sum() > 0:
        raise ValueError("すでに登録されています")
    
    # 重複していなければ、データベースにデータを追加します
    df_add = pd.DataFrame(bookInfo, index=[0])
    df =pd.concat([df, df_add], ignore_index=True)
    df.to_csv("bookInfoAutomation.csv", encoding="UTF-8")

    return


def copyAndName(originFilePath: str, yieldFolderPath: str, bookInfo: dict) -> None:
    """
    与えられた bookInfo をもとに、ファイル名を作成し、その名前のファイルをコピーします。
    ファイル名の例:「本のタイトル_ISBN.pdf」
    Args:
        originFilePath(str): 元ファイルの path
        yieldFilePath(str): 改名後のファイルを置く path
        bookInfo(dict): getInfo で取得した本の情報。IBSNと本のタイトルが含まれています。
    Returns:
        None: ファイルをコピーしておわりです。
    Raises:
        工事中

    """
    # ファイル名を作成します。getCode関数で生成された dict をもちいて、「本のタイトル_ISBN.pdf」
    # となるようなファイル名を作ります。
    title = bookInfo["title{}"]
    ISBN = bookInfo["ISBN"]
    f_name = title + "_" + ISBN + ".pdf"


    # 作ったファイル名が windows の禁止文字を含んでいないか確認し、禁止文字を置き換えます。
    replace_with = "⦸"
    new_name = re.sub(r'[\/:*?"<>|]', replace_with, f_name)
    new_name = os.path.join(yieldFolderPath, new_name)

    # 名前が付いたファイルをコピーします。
    shutil.copy(originFilePath, new_name)

    return


def listUpPathesInFolder(folderPath: str):
    pathes = os.listdir(folderPath)
    yieldPathes = []
    for i in pathes:
        yieldPathes.append(os.path.join(folderPath, i))
    
    return yieldPathes



# main
def main():
    folderPath = ".\\test"
    yieldFolderPath = ".\\yield"
    errorPathes = []

    for i in listUpPathesInFolder(folderPath):
        bookJan = readCode(i, 5, "end")
        if isinstance(bookJan, str):
            errorPathes.append(bookJan)
            continue
        bookInfo = getInfo(bookJan["ISBN"])
        addDatabase(bookInfo)
        copyAndName(i, yieldFolderPath, bookInfo)

    print(f"これらのファイルから書籍JANコードを見つけられませんでした。\n")
    for i in errorPathes:
        print(i)

if __name__ == "__main__":
    main()