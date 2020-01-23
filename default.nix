{
  pkgs ? import <nixpkgs> {},
}:
with pkgs;
stdenv.mkDerivation rec {
  name = "process-book-html";
  version = "1.0.0";
  srcs = [
    ./process_book_html.py
  ];
  buildInputs = [
    (python3.withPackages (p: with p; [
      beautifulsoup4
      lxml
      ptpython
      termcolor
    ]))
    (texlive.combine rec {
      inherit (texlive) scheme-small collection-xetex
        collection-latexrecommended
        preview dvisvgm newtx fontaxes
        amsfonts amsmath standalone stix2-type1 stix2-otf unicode-math;
    })
    ghostscript
    stix-two
    (import ./snuggletex.nix {})
  ];
}
