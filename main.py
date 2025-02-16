# 組み込みモジュール
import re
from typing import Literal, Union
import tempfile
import os
import shutil
import xml.etree.ElementTree as ET
import time
# 外部モジュール
from PIL import Image
import pyzbar.pyzbar as pyzbar
import requests
import pandas as pd
import pymupdf
import configparser


def read_code(pdf_path: str, number_of_pages: int, starting_point: Literal["end", "first"]) -> Union[dict, str]:
    """
    指定されたpathにあるpdfファイルの、指定されたページ範囲から、書籍JANコードを探して読み取ります。
    そして、書籍JANコードをISBNとdetailCodeが内包された辞書型にして返します。
    もしも、PDFファイル中に書籍JANコードがなかったのなら、そのPDFファイルの Path を返します。
    Args:
        pdf(str): PDFファイルへのパス
        number_of_pages(int): どれくらいの量のページから書籍JANコードを探すか指定します。
        starting_point("end" or "first"):
            "end": 後ろのページから書籍JANコードを探します
            "first": 先頭のページから書籍JANコードを探します

    Returns:
        dict: ISBNと詳細コードを格納した辞書。フォーマットは以下の通り:
            {
                "isbn": str,         # ISBNコード
                "detailed_code": str   # 図書分類コードおよび図書本体価格を含むコード
            }
        str: バーコードを見つけられなかった pdf の path
    Raises:
        ValueError("{pdf_path}は、PDFではありません")
            与えられたファイルが、PDF ではないときに表示されます。
        ValueError("範囲内に有効なバーコードが見つかりませんでした。")

    Notes: 
        書籍JANコード は、２つのバーコードのセットで構成されています。
        一段目には、ISBNが内包されています。978から始まる整数の列です。
        二段目には、図書分類コードおよび、図書本体価格が内包されています（便宜上、"detailed_code"と表記します）。192から始まる整数の列です。
        接頭辞である978と192を用いて、ISBNとdetailCodeを見分けています。
    """
    book_JAN = {}

    if os.path.splitext(pdf_path)[1] != ".pdf":
        raise ValueError(f"{os.path.basename(pdf_path)} は、PDF ではありません。")
    doc = pymupdf.Document(pdf_path)

    # 指定されたページ数と、ページ数を数え始める場所から、読み取るページ範囲を作成します。
    # 後ろからページ数を数え、指定されたページ数分のページ範囲を作成
    if starting_point == "end":
        number_of_pages = -1 * number_of_pages
        page_range = range(number_of_pages,0)
    # 前からページ数を数え、指定されたページ数分のページ範囲を作成
    elif starting_point == "first":
        page_range = range(0, number_of_pages)
    # ページ範囲が適切か確認します。
    if len(page_range) > doc.page_count:
            raise ValueError(f"読み込もうとしているページ数が、PDF の全ページ数を超えています。 読み込もうとしているページ数:{len(page_range)} > PDF の全ページ数:{doc.page_count}")

    # 指定されたページ範囲から、書籍JANコードを探します。
    # 指定されたページ範囲について、それぞれのページを画像に変換します。その画像からバーコードを読み取ります。
    for i in page_range:
        with tempfile.NamedTemporaryFile(suffix=".png") as temp_f:
            zoom_x = 2.0  # horizontal zoom
            zoom_y = 2.0  # vertical zoom
            mat = pymupdf.Matrix(zoom_x, zoom_y)
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat)
            pix.save(temp_f.name)
            with Image.open(temp_f.name) as temp_pic:
                bcodes = pyzbar.decode(temp_pic, symbols=[pyzbar.ZBarSymbol.EAN13])

        # 書籍JANコードがあるか判断します。
        # 初めに、数で判断します。書籍JANコードは、２つのバーコードのセットであるため、２つあるかで判断します。
        if len(bcodes) <= 1 or len(bcodes) >= 3:
            continue
        # バーコードが２つあったら、JANコードの振り分けをします。書籍JANコードの接頭辞をもちいて、ISBNと詳細コードに分類します。
        for i in bcodes:
            if str(int(i.data)).startswith(("978","979")):
                book_JAN["isbn"] = str(int(i.data))
            elif str(int(i.data)).startswith("192"):
                book_JAN["detailed_code"] = str(int(i.data))
            else:
                pass
        # 書籍JANコードがそろったなら、バーコード読み取りをやめます。
        if len(book_JAN) == 2:
            break
    # もし、指定されたページ範囲から書籍JANコードを見つけられなかった場合、そのPDFのpathを返します。
    if bool(book_JAN):
        return book_JAN
    else:
        return pdf_path


def get_info(isbn: str) -> dict:
    """
    ISBN(str)から本の情報(dict)を取得します。
    国立国会図書館が提供する、「外部提供インターフェース」の「OpenSearch」をもちいて、取得しています。
    Args:
        isbn(str):本のISBN
    Returns:
        book_info(dict):本の情報が詰まった辞書
    Raises:
        ValueError("国立国会図書館で、指定された ISBN をもつ書籍情報を見つけられませんでした。")
    """
    # 国立国会図書館OpenSearchのエンドポイントURLと、与えられたISBNをもちいて、
    # HTTPリクエストします
    END_POINT_URL = "https://ndlsearch.ndl.go.jp/api/opensearch?isbn="
    url = END_POINT_URL + str(isbn)
    res = requests.get(url)

    # 帰ってきた XMLデータ の中から、書籍情報を取り出して、dict に変換します。
    root = ET.fromstring(res.text)
    xml_book_info = root.find(".//item")
    if xml_book_info is None:
        raise ValueError("国立国会図書館から、指定された ISBN をもつ書籍情報を見つけられませんでした。")
    book_info = {}
    book_info["isbn"] = isbn
    for i in xml_book_info:
        book_info[f"{i.tag + str(i.attrib)}"] = i.text

    return book_info


def add_database(book_info: dict) -> None:
    """
    本の情報(dict)を、データベースに格納します。
    データベースがなかったなら、新しく作成（ファイル名:"book_infoAutomation.csv"）されます
    Args:
        book_info(dict): 本の情報が詰まった辞書
    return:
        None
    """
    if not os.path.isfile("book_infoAutomation.csv"):
        df = pd.DataFrame(columns=book_info.keys())
        df.to_csv("book_infoAutomation.csv", encoding="UTF-8")
    
    # データベースを読み込んで、同一の ISBN をもつ行があるか検索します。そしてあった（重複）なら、データを追加しません
    df = pd.read_csv("book_infoAutomation.csv", index_col=0)
    result = (df["isbn"] == int(book_info["isbn"]))
    if result.sum().sum() > 0:
        print("すでに登録されています")
    
    # 重複していなければ、データベースにデータを追加します
    df_add = pd.DataFrame(book_info, index=[0])
    df = pd.concat([df, df_add], ignore_index=True)
    df.to_csv("book_infoAutomation.csv", encoding="UTF-8")
    return


def copy_and_name(origin_file_path: str, yield_folder_path: str, book_info: dict) -> None:
    """
    与えられた book_info をもとに、ファイル名を作成し、その名前のファイルをコピーします。
    ファイル名の例:「本のタイトル_ISBN.pdf」
    Args:
        origin_file_path(str): 元ファイルの path
        yieldFilePath(str): 改名後のファイルを置く path
        book_info(dict): get_info で取得した本の情報。IBSNと本のタイトルが含まれています。
    Returns:
        None: ファイルをコピーしておわりです。
    """
    # ファイル名を作成します。getCode関数で生成された dict をもちいて、「{本のタイトル}_{isbn}.pdf」
    # となるようなファイル名を作ります。
    title = book_info["title{}"]
    isbn = book_info["isbn"]
    book_desprictions = book_info["description{}"][3:].split(",")

    try:
        book_issue_num = str(int(book_desprictions[0]))
        book_issue_num = book_issue_num + "巻_"
    except:
        book_issue_num = ""

    f_name = title + "_" + book_issue_num + isbn + ".pdf"

    # 作ったファイル名が windows の禁止文字を含んでいないか確認し、禁止文字を置き換えます。
    replace_with = "⦸"
    new_name = re.sub(r'[\/:*?"<>|]', replace_with, f_name)
    new_name = os.path.join(yield_folder_path, new_name)

    # 名前が付いたファイルをコピーします。
    shutil.copy(origin_file_path, new_name)
    return


def listUpPathesInFolder(folderPath: str):
    pathes = os.listdir(folderPath)
    yield_pathes = []
    for i in pathes:
        yield_pathes.append(os.path.join(folderPath, i))
    return yield_pathes



# main
def main():
    # config.ini から、処理前のPDF がある Path と、処理後のPDFを入れる Path を読み込みます。
    config_ini = configparser.ConfigParser()
    config_ini.read("config.ini", encoding="utf-8")
    before_processing = config_ini["DEFAULT"]["before_processing"]
    after_processing = config_ini["DEFAULT"]["after_processing"]
    # 処理できなかった PDF の Path を記録する List です
    error_pathes = []

    # beforeProcessig 内の PDF ファイルについて処理を繰り返します
    files = os.listdir(before_processing)
    pdf_files = [os.path.join(before_processing, i) for i in files if i.endswith(".pdf")]
    for i in pdf_files:
        start = time.time()
        # 書籍JANコードを読み込みます。
        book_JAN = read_code(i, 3, "end")

        # read_code が、読み込めたかどうか確認します。
        # 
        if isinstance(book_JAN, str):
            error_pathes.append(book_JAN)
            continue

        # 情報を取り込みます。
        try:
            book_info = get_info(book_JAN["isbn"])
        except:
            continue

        # データベースに追加します
        try:
            add_database(book_info)
        except:
            continue
            
        # コピーします
        copy_and_name(i, after_processing, book_info)
        end = time.time()
        print(f"{str(i)}: takes {round(end-start, 3)} seconds.")


    # ISBN を見つけられなかったファイルを挙げて、ISBNを手入力するように誘導します。
    still_cant_find = []
    print(f"===========\nこれらのファイルから書籍JANコードを見つけられませんでした。")
    for i in error_pathes:
        print(i)
    print("===========")
    # 手入力を要求します
    for i in error_pathes:
        print(f"この本のISBNは何ですか？: {i}\nわからない場合は、\"!\"を入力してください")
        isbn = input(">>>")
        if isbn == "!":
            still_cant_find.append(i)
            continue
        else:
            pass
        start = time.time()
        book_info = get_info(isbn)
        add_database(book_info)
        copy_and_name(i, after_processing, book_info)
        end = time.time()
        print(f"{str(i)}: takes {round(end-start, 3)} seconds.")

    print(f"===========\nこれらのファイルから書籍情報を見つけられませんでした。")
    for i in still_cant_find:
        print(i)
    print("===========")
    return

if __name__ == "__main__":
    main()