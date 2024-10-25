from typing import Literal
from pdf2image import convert_from_path
import pypdf


def pageSelector(pdfPath:str , pageAmount:int, startingPoint: Literal["end", "first"]) -> dict:
    """
    PDF のページ範囲を指定します。後ろからまたは先頭からページ数を指定して範囲を計算します。

    Args:
        pdfPath (str): ページ数を取得するPDFファイルのパス。
        pageAmount (int): 取り出したいページ数。
        startingPoint (str): "end"で最後から数えるか、"first"で最初から数えるかを指定します。

    Returns:
        dict: 指定された範囲の最初と最後のページ番号を格納した辞書。{"first_page": 開始ページ, "last_page": 終了ページ}

    Raises:
        ValueError: ページ範囲がPDFの総ページ数を超えている場合に発生します。
    """
    # 指定された PDF のページ数を確認します
    pdf = pypdf.PdfReader(pdfPath)
    number_of_pages = len(pdf.pages)

    # ページ範囲を生成します。先頭からページ数を数えるか、後ろからページ数を数えるかで分岐します
    if startingPoint == "end":
        last_page = number_of_pages
        first_page = number_of_pages - (pageAmount - 1)
        if first_page < 1:
            raise ValueError(f"Out of range: The number of page can not be minus or zero, but the calculated first page is {first_page}.")
    elif startingPoint == "first":
        first_page = 1
        last_page = number_of_pages + (pageAmount - 1)
        if last_page > number_of_pages:
            raise ValueError(f"Out of range: The PDF has {number_of_pages} pages, but the calculated first page is {last_page}.")

    # 辞書型に格納します
    pageRange = {"first_page": first_page, "last_page": last_page}

    return pageRange


pageRange = pageSelector("test-comic.pdf", 2, startingPoint="end")
im = convert_from_path("test-comic.pdf", first_page=pageRange["first_page"], last_page=pageRange["last_page"])

for idx, img in enumerate(im):
    img.save(f"page_{idx}.png", format="PNG")
