#!/usr/bin/env python3.7

import subprocess
from dataclasses import dataclass
from os import path
import os
import re
from typing import Optional, List
import difflib
import sys
import math
import itertools

from bs4 import BeautifulSoup, NavigableString, Comment, Tag, Doctype
import bs4
from termcolor import colored, cprint

import cache

BOOK_SRC_DIR = 'information-retrieval'
ONLINE_SRC_BASE = 'https://nlp.stanford.edu/IR-book/html/htmledition/'
OUTPUT_DIR = 'output'

NAVPANEL_START = '<!--Navigation Panel-->'
NAVPANEL_END  = '<!--End of Navigation Panel-->'

CHILD_LINKS_START = '<!--Table of Child-Links-->'
CHILD_LINKS_END = '<!--End of Table of Child-Links-->'

IRBOOK_MARKER = r'''
<BODY >
<H1>Introduction to Information Retrieval</H1>
'''
CONVERSION_COMMENT_MARKER = 'Converted with LaTeX2HTML 2002-2-1 (1.71)'

LEFT_FLOOR = r'\mbox{LEFT FLOOR PROCESS-BOOK-HTML}'
LEFT_FLOOR_MATHML = '<mtext>LEFT FLOOR PROCESS-BOOK-HTML</mtext>'
LEFT_FLOOR_ACTUAL = '<mo>&#8970;</mo>'
RIGHT_FLOOR = r'\mbox{RIGHT FLOOR PROCESS-BOOK-HTML}'
RIGHT_FLOOR_MATHML = '<mtext>RIGHT FLOOR PROCESS-BOOK-HTML</mtext>'
RIGHT_FLOOR_ACTUAL = '<mo>&#8971;</mo>'

NEWCOMMANDS = {
    r'\langle': r'\newcommand\langle{\left<}',
    r'\rangle': r'\newcommand\rangle{\right>}',
    r'\lfloor': r'\newcommand\lfloor{' + LEFT_FLOOR + '}',
    r'\rfloor': r'\newcommand\rfloor{' + RIGHT_FLOOR + '}',
    r'\weestrut': r'\newcommand\weestrut{}',
    r'\medstrut': r'\newcommand\medstrut{}',
    r'\upstrut': r'\newcommand\upstrut{}',
    r'\begin{equation}': r'\newenvironment{equation}{\[}{\]}',
    r'\framebox': r'\newcommand\framebox[1]{\fbox{#1}}',
    r'\cal': r'\newcommand\cal[1]{\mathcal{#1}}',
    r'\phantom': r'\newcommand\phantom[1]{\hspace{0.5em}}',
    r'\ne': r'\newcommand\ne{\not=}',
    r'\thinspace': r'\newcommand\thinspace{}',

    r'\termf': r'\newcommand\termf{\mathrm{tf}}',
    r'\collf': r'\newcommand\collf{\mathrm{cf}}',
    r'\docf': r'\newcommand\docf{\mathrm{df}}',
    r'\oper': r'\newcommand\oper[1]{\textrm{#1}}',
    r'\tcjclass': r'\newcommand\tcjclass{c}',
    r'\tcposindex': r'\newcommand\tcposindex{k}',
    r'\unicode': r'\newcommand\unicode[2]{#2}', # ???
    r'\mthatwask': r'\newcommand\mthatwask{m}',
    r'\nthatwasell': r'\newcommand\nthatwasell{n}',
    r'\twasx': r'\newcommand\twasx{t}',
    r'\matrix': r'\newcommand\matrix[1]{#1}',
    r'\lsimatrix': r'\newcommand\lsimatrix{C}',
    r'\query': r'\newcommand\query[1]{\textsf{#1}}',
    r'\term': r'\newcommand\term[1]{\textsf{#1}}',
    r'\class': r'\newcommand\class[1]{\textit{#1}}',
    r'\onedoc': r'\newcommand\onedoc{d}',
    r'\onedoclabeled': r'\newcommand\onedoclabeled{\left< d, c \right>}',
    r'\docset': r'\newcommand\docset{D}',
    r'\argmin': r'\newcommand\argmin{\mathrm{arg min}}',
    r'\argmax': r'\newcommand\argmax{\mathrm{arg max}}',
    r'\dlenmax': r'\newcommand\dlenmax{L_{\max}}',
    r'\tcword': r'\newcommand\tcword{t}',
    r'\observationo': r'\newcommand\observationo{N}',
    r'\wvar': r'\newcommand\wvar{U}',
    r'\xvar': r'\newcommand\xvar{X}',
    r'\docsetlabeled': r'\newcommand\docsetlabeled{\mathbb{D}}',
    r'\ktopk': r'\newcommand\ktopk{k}',
    r'\oldell': r'\newcommand\oldell{i}',
    r'\lsinoterms': r'\newcommand\lsinoterms{M}',
    r'\lsinodocs': r'\newcommand\lsinodocs{N}',
    r'\colon': r'\newcommand\colon{:}', # ???
    r'\begin{example}': r'\newenvironment{example}{}{}',
}


ENV_START = re.compile(r'\\begin{[a-zA-Z]+\*?}')
TEX_ONE_LETTER = re.compile(r'^\$([a-zA-Z])\$$')
TEX_KERN_RE = re.compile(r'\\kern\s*[0-9]*(\.[0-9]+)?(pt|in|cm|em)')
TABULAR_START = re.compile(r'\\begin{tabular}{([^}]+)}')
TABULAR_END = r'\end{tabular}'

def read(fname: str) -> str:
    with open(fname, encoding='utf-8') as f:
        return f.read()


def soups(page: str, parser='lxml') -> BeautifulSoup:
    return BeautifulSoup(page, parser)


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

    # Patch up \lfloor and \rfloor
    return (proc.stdout.replace(LEFT_FLOOR_MATHML, LEFT_FLOOR_ACTUAL)
            .replace(RIGHT_FLOOR_MATHML, RIGHT_FLOOR_ACTUAL)
    )


def tex_to_mathml(tex: str) -> str:
    display_start = r'$\displaystyle'
    display_end = '$'
    if tex.startswith(display_start) and tex.endswith(display_end):
        tex = r'\[' + tex[len(display_start):-len(display_end)] + r'\]'

    textstyle_start = r'$\textstyle'
    if tex.startswith(textstyle_start):
        tex = tex.replace(textstyle_start, '$')

    tex = tex.replace(r'\char93', r'\#')
    tex = TEX_KERN_RE.sub('', tex)

    if tex == r'$\langle$':
        # ugh, edge cases
        tex = r'$\left<\right.$'
    elif tex == r'$\rangle$':
        tex = r'$\left.\right>$'
    elif tex == r'$\ldots\rangle$':
        tex = r'$\ldots\left.\right>$'

    tex = TABULAR_START.sub(r'\\begin{array}{\1}', tex)
    tex = tex.replace(TABULAR_END, r'\end{array}')

    tex = (tex.replace(r'\big(', r'\left(')
           .replace(r'\big)', r'\right)')
           .replace(r'\nolimits', ''))

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
    for comment in parent.previous_elements:
        if isinstance(comment, Comment):
            found_comment = True
            break

    if not found_comment:
        return None

    math_marker = 'MATH\n'
    tex = comment.strip()
    if tex.startswith(math_marker):
        tex = tex[len(math_marker):].strip()

    if tex.startswith(CONVERSION_COMMENT_MARKER):
        return None

    if not check_tex_sameish(tex, el['alt']):
        return None

    comment.replace_with('')
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

    # Delete elements that epub doesn't like
    for el in chapter_soup.find_all('meta'):
        el.decompose()

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
        if type(s) in [Comment, bs4.Doctype, bs4.ProcessingInstruction, bs4.Declaration]:
            continue
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

        # cross-reference symbol
        if alt == '[*]':
            img.parent.string = '‡'
            continue

        mathml = trivial_tex_to_mathml(alt)
        if mathml is None:
            # Otherwise, give SnuggleTeX a try:
            try:
                mathml = tex_to_mathml(alt)
            except TeXRenderError as e:
                e.context = img.parent
                raise

        img.replace_with(soups(mathml, 'html.parser'))

    # delete empty children at the end of the docment
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

    # this prevents a file from being invalid xhtml lol
    for bad_a in chapter_soup.find_all('a'):
        if bad_a.has_attr('wikipedia:general'):
            del bad_a['wikipedia:general']
            break

    # # We're renaming everything to .xhtml
    # for el in itertools.chain(chapter_soup.find_all('link'),
    #                           chapter_soup.find_all('a')):
    #     if el.has_attr('href') and not el['href'].startswith('http'):
    #         el['href'] = el['href'].replace('.html', '.xhtml')

    # Get rid of naughty attributes
    for el in chapter_soup.find_all(True):
        el['class'] = ''
        for attr in ['align', 'valign', 'cellpadding', 'border', 'nowrap', 'compact']:
            if el.has_attr(attr):
                el['class'] += attr + '-' + el[attr].lower()
                del el[attr]

        if el.has_attr('width'):
            if el['width'] == '100%':
                el['class'] += ' full-width'
            else:
                el['class'] += ' width-' + el['width']
            del el['width']

        if not el['class']:
            del el['class']

    for el in chapter_soup.find_all('br'):
        if el.has_attr('clear'):
            del el['clear']

    for el in chapter_soup.find_all('tt'):
        el.name = 'code'

    chapter_soup.html.head.append(
        chapter_soup.new_tag('meta', charset='utf-8')
    )
    chapter_soup.html.head.append(
        chapter_soup.new_tag(
            'link',
            rel='stylesheet',
            type='text/css',
            href='Styles/book.css',
        )
    )

    first_child = next(chapter_soup.children)
    if isinstance(first_child, Doctype):
        # XHTML has no doctype, and Doctype has no decompose method
        # first_child.replace_with(soups('<!DOCTYPE html>'))
        first_child.replace_with(Doctype('html'))

    for el in chapter_soup.children:
        if isinstance(el, Comment) and el.startswith(CONVERSION_COMMENT_MARKER):
            el.replace_with('')
            break

    # chapter_soup.find('html')['xmlns:epub'] = 'http://www.idpf.org/2007/ops'

    # chapter_soup.smooth()
    return chapter_soup



def output_files(ext: Optional[str] = None) -> List[str]:
    return [
        path.realpath(path.join(OUTPUT_DIR, p))
        for p in sorted(os.listdir(OUTPUT_DIR))
        if ext is None or p.endswith(ext)
    ]


def main():
    src_dir = path.realpath(BOOK_SRC_DIR)
    chapters = [
        path.join(src_dir, p)
        for p in sorted(os.listdir(src_dir))
        if p.endswith('.html')
    ]
    skipping = True
    skip_until = None

    digits = math.ceil(math.log10(len(chapters)))
    fmt = f'{digits}d'

    if not path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    cache.init_cache()

    for i, chapter_filename in enumerate(chapters):
        i += 1
        if skip_until is None or chapter_filename.endswith(skip_until):
            skipping = False
        output_basename = path.basename(chapter_filename)
        output_filename = path.join(OUTPUT_DIR, output_basename)
        print(colored(
            '[{}/{}]:'.format(format(i, fmt), len(chapters)),
            'green', attrs=['bold']),
              output_basename)
        if skipping:
            continue
        with open(output_filename, 'w') as f:
            chapter_txt = read(chapter_filename)
            try:
                chapter_processed = process_chapter(chapter_txt)
            except TeXRenderError as e:
                cprint('Error while converting TeX to MathML', 'red', attrs=['bold'])
                print(e.proc)
                print(e.proc.output.strip())
                cprint(e.proc.stderr.strip(), 'red')
                cprint('TeX source:', 'red', attrs=['bold'])
                print(e.src)
                if e.context:
                    cprint('Page context:', 'red', attrs=['bold'])
                    print(e.context)
                print('Check the chapter online:', colored(
                    ONLINE_SRC_BASE + output_basename,
                    'cyan', attrs=['underline']
                ))
                sys.exit(1)

            f.write(str(process_chapter(read(chapter_filename))))

    cprint('Done!', 'green', attrs=['bold'])


if __name__ == '__main__':
    main()
