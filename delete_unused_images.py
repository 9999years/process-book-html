#!/usr/bin/env python3.7

from os import path
import os

import process_book_html

def main():
    out_files = [
        path.join(process_book_html.OUTPUT_DIR, p)
        for p in sorted(os.listdir(process_book_html.OUTPUT_DIR))
    ]

    images = {
        p for p in out_files if p.endswith('.png')
    }

    html_files = [
        p for p in out_files if p.endswith('.html')
    ]

    for fn in html_files:
        txt = process_book_html.read(fn)
        remove_images = set()

        for img in images:
            if path.basename(img) in txt:
                # the image's file is mentioned in the page
                remove_images.add(img)

        if len(remove_images) > 0:
            images.difference_update(remove_images)

    for image in images:
        os.remove(image)

if __name__ == '__main__':
    main()
