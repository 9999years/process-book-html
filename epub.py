#! /usr/bin/env python3.7

import os
from os import path
import uuid
from typing import List, Tuple, Optional, Union
import sys

from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from termcolor import cprint, colored

import process_book_html

book_uuid = '95b04cc8289e40f6bd8b7399ce324a93'
isbn = '0521865719'
language = 'en'
title = 'Introduction to Information Retrieval'
author = 'Christopher D. Manning, Prabhakar Raghavan, & Hinrich Schütze'
published = '2008-07-01'
publisher = 'Cambridge University Press'
cover_fname = 'cover.jpg'
contents_fname = 'contents-1.xhtml'
output_filename = 'information-retrieval.epub'
css_filename = 'book.css'

def get_uuid() -> str:
    return 'b' + uuid.uuid1().hex


TocEntry = Union[
    epub.Link,
    Tuple[epub.Link, 'TocList']
]
TocList = List[TocEntry]
UUIDList = List[str]


def generate_toc(contents: BeautifulSoup, uids: dict) -> (TocList, UUIDList):
    def make_toc_li(li: BeautifulSoup, toc: TocList):
        href = li.a['href']
        link = epub.Link(
            href=href,
            title=str(li.a.string),
            uid=uids[href],
        )
        spine.append(uids[href])
        not_added_xhtml_files.discard(href)

        if li.ul:
            sub_toc = []
            toc.append((link, sub_toc))
            make_toc_ul(li.ul, sub_toc)
        else:
            toc.append(link)

    def make_toc_ul(ul: BeautifulSoup, toc: TocList):
        for li in ul.find_all('li', recursive=False):
            make_toc_li(li, toc)

    irbook = epub.Link(
        uid=uids['irbook.xhtml'],
        href='irbook.xhtml',
        title='Introduction to Information Retrieval',
    )
    toc = [irbook]
    spine = [
        'cover',
        irbook.uid
    ]

    not_added_xhtml_files = set(map(path.basename, process_book_html.output_files('.xhtml')))
    not_added_xhtml_files.discard(irbook.href)
    make_toc_ul(contents.find('ul'), toc)
    spine.extend(map(uids.__getitem__, not_added_xhtml_files))

    return toc, spine


def get_toc(uids: dict) -> (TocList, UUIDList):
    contents_soup = process_book_html.soup(output_path(contents_fname))
    return generate_toc(contents_soup, uids)


def doc_title(html: str) -> str:
    soup = BeautifulSoup(html, 'lxml')
    return str(soup.find('title').string)

def output_path(p: str) -> str:
    return path.join(process_book_html.OUTPUT_DIR, p)


def make_epub() -> epub.EpubBook:
    book = epub.EpubBook()
    book.set_identifier(book_uuid)
    book.set_language(language)
    book.set_title(title)
    book.add_author(author)

    uids = {
        cover_fname: 'cover-image',
    }

    with open(output_path(cover_fname), 'rb') as f:
        book.set_cover(
            file_name=cover_fname,
            content=f.read(),
        )

    for filename in process_book_html.output_files('.xhtml'):
        uid = get_uuid()
        uids[path.basename(filename)] = uid

        content = process_book_html.read(filename)
        chapter = epub.EpubHtml(
            uid=uid,
            title=doc_title(content),
            file_name=path.basename(filename),
            lang=language,
            content=content,
        )
        book.add_item(chapter)

    for filename in process_book_html.output_files('.png'):
        uid = get_uuid()
        uids[path.basename(filename)] = uid

        with open(filename, 'rb') as f:
            img_data = f.read()
            img = epub.EpubItem(
                file_name=path.basename(filename),
                content=img_data,
                uid=uid,
            )
            book.add_item(img)

    with open(css_filename) as css:
        uids[css_filename] = 'book_css'
        css_content = css.read()
        css_item = epub.EpubItem(
            uid=uids[css_filename],
            file_name=path.join('Styles', css_filename),
            media_type='text/css',
            content=css_content,
        )
        book.add_item(css_item)

    book.toc, book.spine = get_toc(uids)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    return book

def check_book(book):
    found_bad = False
    for item in book.get_items():
        for attr in ['file_name', 'id', 'media_type']:
            if type(getattr(item, attr)) not in [bytes, str]:
                found_bad = True
                cprint(f'Item {item} has bad {attr} {getattr(item, attr)}', 'red', attrs=['bold'])
    return found_bad

def main():
    # if path.exists(output_filename):
    #     cprint(f'Output file {output_filename} already exists, refusing to overwrite',
    #            'red', attrs=['bold'])
    #     sys.exit(1)

    book = make_epub()
    if check_book(book):
        sys.exit(1)

    epub.write_epub(
        output_filename,
        book,
        {
            'play_order':  {'enabled': True, 'start_from': 1}
        }
    )
    cprint(f'Wrote {output_filename} successfully!', 'green', attrs=['bold'])

if __name__ == '__main__':
    main()
