#!/usr/bin/env python3.7

import subprocess
from dataclasses import dataclass
from os import path
import os
import re
from typing import Optional
import difflib
import sys

from bs4 import BeautifulSoup, NavigableString, Comment, Tag

import cache

BOOK_SRC_DIR = 'book-src'
ONLINE_SRC_BASE = 'https://nlp.stanford.edu/IR-book/html/htmledition/'

CONTENTS_FILE = '/home/becca/Downloads/ir/IR-book/html/htmledition/contents-1.html'

NAVPANEL_START = '<!--Navigation Panel-->'
NAVPANEL_END  = '<!--End of Navigation Panel-->'

CHILD_LINKS_START = '<!--Table of Child-Links-->'
CHILD_LINKS_END = '<!--End of Table of Child-Links-->'

IRBOOK_MARKER = r'''
<BODY >
<H1>Introduction to Information Retrieval</H1>
'''

NEWCOMMANDS = {
    r'\langle': r'\newcommand\langle{\left<}',
    r'\rangle': r'\newcommand\rangle{\right>}',
    r'\weestrut': r'\newcommand\weestrut{}',
    r'\medstrut': r'\newcommand\weestrut{}',
    r'\begin{equation}': r'\newenvironment{equation}{\[}{\]}',
    r'\framebox': r'\newcommand\framebox[1]{\fbox{#1}}',

    r'\termf': r'\newcommand\termf{\mathrm{tf}}',
    r'\tcjclass': r'\newcommand\tcjclass{c}',
    r'\tcposindex': r'\newcommand\tcposindex{k}',
    r'\unicode': r'\newcommand\unicode[2]{#2}', # ???
    r'\mthatwask': r'\newcommand\mthatwask{m}',
    r'\nthatwasell': r'\newcommand\nthatwasell{n}',
    r'\lsimatrix': r'\newcommand\lsimatrix{C}',
    r'\query': r'\newcommand\query[1]{\textsf{#1}}',
    r'\onedoc': r'\newcommand\onedoc{d}',
    r'\argmin': r'\newcommand\argmin{\mathrm{arg min}}',
    r'\dlenmax': r'\newcommand\dlenmax{L_{\max}}',
    r'\tcword': r'\newcommand\tcword{t}',
    r'\observationo': r'\newcommand\observationo{N}',
}

TOC_PREFIX = r'''
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
   "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="urn:uuid:12644d5f-5e07-4d28-8d05-035a063edd31" />
    <meta name="dtb:depth" content="3" />
    <meta name="dtb:totalPageCount" content="0" />
    <meta name="dtb:maxPageNumber" content="0" />
  </head>
<docTitle>
  <text>Introduction to Information Retrieval</text>
</docTitle>
<docAuthor>
  <text>Christopher D. Manning, Prabhakar Raghavan, and Hinrich Schütze</text>
</docAuthor>
'''

TOC_POSTFIX = r'''
</ncx>
'''

ENV_START = re.compile(r'\\begin{[a-zA-Z]+\*?}')

TEX_ONE_LETTER = re.compile(r'^\$([a-zA-Z])\$$')

def read(fname: str) -> str:
    with open(fname, encoding='utf-8') as f:
        return f.read()


def soups(page: str) -> BeautifulSoup:
    return BeautifulSoup(page, 'lxml')


def soup(fname: str) -> BeautifulSoup:
    return soups(read(fname))


def delete_delimited_chunk(text: str, start: str, end: str) -> str:
    inx = text.index(start)
    end_idx = text.index(end, inx)
    return text[:inx] + text[end_idx + len(end):]


@dataclass
class TeXRenderError(BaseException):
    proc: subprocess.CalledProcessError
    src: str
    context: Optional[BeautifulSoup] = None


def tex_to_mathml_(tex: str) -> str:
    prefix = []

    for cmd, defn in NEWCOMMANDS.items():
        if cmd in tex:
            prefix.append(defn)

    tex = ''.join(prefix) + tex

    proc = subprocess.run(
        ['snuggletex', '-'],
        input=tex,
        capture_output=True,
        text=True,
        encoding='utf-8',
    )
    if proc.returncode != 0 or proc.stderr.strip():
        raise TeXRenderError(
            proc=subprocess.CalledProcessError(
                returncode=proc.returncode,
                cmd=proc.args,
                output=proc.stdout,
                stderr=proc.stderr,
            ),
            src=tex,
        )

    return proc.stdout


def tex_to_mathml(tex: str) -> str:
    display_start = r'$\displaystyle'
    display_end = '$'
    if tex.startswith(display_start) and tex.endswith(display_end):
        tex = r'\[' + tex[len(display_start):-len(display_end)] + r'\]'

    textstyle_start = r'$\textstyle'
    if tex.startswith(textstyle_start):
        tex = tex.replace(textstyle_start, '$')

    if tex == r'$\langle$':
        # ugh, edge cases
        tex = r'$\left<\right.$'
    elif tex == r'$\rangle$':
        tex = r'$\left.\right>$'
    elif tex == r'$\ldots\rangle$':
        tex = r'$\ldots\left.\right>$'

    return cache.ensure(tex, tex_to_mathml_)


def trivial_tex_to_mathml(tex: str) -> Optional[str]:
    if tex == r'\l':
        return 'ł'

    return None


def check_tex_sameish(comment_src: str, alt_src: str) -> bool:
    while ENV_START.match(comment_src):
        comment_src = ENV_START.sub('', comment_src)

    while ENV_START.match(alt_src):
        alt_src = ENV_START.sub('', alt_src)

    comment_src.replace('|', r'\vert')

    ellipsis_index = alt_src.find('...')

    matcher = difflib.SequenceMatcher()
    matcher.set_seqs(comment_src, alt_src)

    comment_inx, alt_inx, match_len = matcher.find_longest_match(
        0, min(ellipsis_index, len(comment_src)),
        0, ellipsis_index
    )

    return match_len >= (ellipsis_index * 0.8)


def expand_ellipsized(el: Tag) -> Optional[str]:
    expected_parents = ['td', 'tr', 'table']
    for expect, parent in zip(expected_parents, el.parents):
        if parent.name != expect:
            return None

    found_comment = False
    for prev_el in parent.previous_elements:
        if isinstance(prev_el, Comment):
            found_comment = True
            break

    if not found_comment:
        return None

    math_marker = 'MATH\n'
    tex = prev_el.strip()
    if tex.startswith(math_marker):
        tex = tex[len(math_marker):].strip()

    if tex.startswith('Converted with LaTeX2HTML'):
        return None

    if not check_tex_sameish(tex, el['alt']):
        return None

    return tex


def process_chapter(chapter: str) -> BeautifulSoup:
    # Trim navpanels
    while NAVPANEL_START in chapter:
        chapter = delete_delimited_chunk(chapter, NAVPANEL_START, NAVPANEL_END)

    # We want to remove the sub-chapter links unless it's the intro page
    if IRBOOK_MARKER not in chapter:
        while CHILD_LINKS_START in chapter:
            chapter = delete_delimited_chunk(chapter, CHILD_LINKS_START, CHILD_LINKS_END)

    chapter_soup = soups(chapter)

    # Delete the "autogenerated page" footer
    address = chapter_soup.find('address')
    if address:
        address.decompose()

    # The link 404's anyways
    css_link = chapter_soup.find('link', href='https://nlp.stanford.edu/IR-book/html/htmledition/irbook.css')
    if css_link:
        css_link.decompose()

    # Who puts a <br> in a header??!
    h1 = chapter_soup.find('h1')
    if h1:
        br = h1.find('br')
        if br:
            br.decompose()

    for s in chapter_soup.find_all(text=re.compile("[`']")):
        old_s = str(s)
        new_s = (
            old_s
            .replace('``', '“')
            .replace("''", '”')
            .replace("'", '’')
            .replace("`", '‘')
        )
        s.replace_with(new_s)

    for img in chapter_soup.find_all('img'):
        alt = img['alt']
        if '...' in alt:
            # they literally deleted half the source i'd need to correctly
            # reproduce the larger figures...
            alt = expand_ellipsized(img)
            if alt is None:
                continue
        if alt.endswith('.html'):
            # wtf are you doing
            continue
        if r'\includegraphics' in alt:
            continue


        mathml = trivial_tex_to_mathml(alt)
        if mathml is None:
            # Otherwise, give SnuggleTeX a try:
            try:
                mathml = tex_to_mathml(alt)
            except TeXRenderError as e:
                e.context = img.parent
                raise

        img.replace_with(soups(mathml))

    annoying_tag_names = ['hr', 'p', 'br']
    empty_tags = ['hr', 'br']
    children = list(chapter_soup.body.find_all(True))
    if children:
        for last_child in reversed(children):
            if last_child.name in annoying_tag_names:
                if last_child.name in empty_tags:
                    last_child.decompose()
                    continue

                if last_child.string and last_child.string.strip():
                    break
                else:
                    last_child.decompose()
            else:
                break

    # this prevents a file from being invalid html lol
    for bad_a in chapter_soup.find_all('a'):
        del bad_a['wikipedia:general']

    return chapter_soup


@dataclass
class NavPoint:
    id: str
    playOrder: int
    labelText: str
    content: str

    def to_bs(self, soup: BeautifulSoup):
        ret = soup.new_tag('navPoint',
                           id=self.id,
                           playOrder=self.playOrder)
        label = soup.new_tag('navLabel')
        labelText = soup.new_tag('text')
        labelText.string = self.labelText
        label.append(labelText)
        ret.append(label)
        content = soup.new_tag('content', src=self.content)
        ret.append(content)
        return ret


def extract_contents(contents: BeautifulSoup) -> BeautifulSoup:
    def mk_navpoint(label: str, href: str) -> NavPoint:
        nonlocal num
        num += 1
        navPoint = NavPoint(
            id=f'navpoint{num}',
            playOrder=num,
            labelText=label,
            content='Text/{}'.format(href),
        ).to_bs(root_soup)
        return navPoint

    def extract_contents_li(li: BeautifulSoup, navMap: BeautifulSoup):
        nonlocal num
        num += 1
        navPoint = mk_navpoint(
            label=str(li.a.string),
            href=li.a['href'],
        )

        navMap.append(navPoint)

        if li.ul:
            extract_contents_ul(li.ul, navPoint)

    def extract_contents_ul(ul: BeautifulSoup, navMap: BeautifulSoup):
        for li in ul.find_all('li', recursive=False):
            extract_contents_li(li, navMap)

    root_soup = BeautifulSoup('<navMap></navMap>', 'lxml-xml')
    navMap = root_soup.find('navMap')
    num = 1

    navMap.append(mk_navpoint(
        label = 'Introduction to Information Retrieval',
        href = 'irbook.html',
    ))

    extract_contents_ul(contents.find('ul'), navMap)

    return navMap


def main():
    src_dir = path.realpath(BOOK_SRC_DIR)
    chapters = [
        path.join(src_dir, p)
        for p in sorted(os.listdir(src_dir))
        if p.endswith('.html')
    ]
    # chapters = [
    #     '/home/becca/Downloads/ir/IR-book/html/htmledition/a-variant-of-the-multinomial-model-1.html',
    #     '/home/becca/Downloads/ir/IR-book/html/htmledition/blocked-storage-1.html'
    # ]
    skipping = True
    skip_until = None # 'centroid-clustering-1.html'
    for chapter_filename in chapters:
        if skip_until is None or chapter_filename.endswith(skip_until):
            skipping = False
        output_filename = path.join('output', path.basename(chapter_filename))
        print(output_filename)
        if skipping:
            continue
        with open(output_filename, 'w') as f:
            chapter_txt = read(chapter_filename)
            try:
                chapter_processed = process_chapter(chapter_txt)
            except TeXRenderError as e:
                print(e.proc)
                print(e.proc.output)
                print(e.proc.stderr)
                print('TeX source:', e.src)
                if e.context:
                    print('Page context:', e.context)
                print('Check the chapter online:', ONLINE_SRC_BASE + path.basename(chapter_filename))
                sys.exit(1)

            f.write(process_chapter(read(chapter_filename)).prettify())

    print('Generating toc.ncx')
    contents = soup(CONTENTS_FILE)
    with open('output/toc.ncx', 'w') as f:
        f.write(TOC_PREFIX)
        f.write(extract_contents(contents).prettify())
        f.write(TOC_POSTFIX)


if __name__ == '__main__':
    main()
