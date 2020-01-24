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
      six
      (import ./ebooklib.nix {inherit pkgs; pythonPackages = p;})
    ]))
    (import ./snuggletex.nix {inherit pkgs;})
    (import ./html2xhtml.nix {inherit pkgs;})
  ];
}
