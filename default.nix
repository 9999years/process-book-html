{
  pkgs ? import <nixpkgs> {},
}:
with pkgs;
stdenv.mkDerivation rec {
  name = "information-retrieval";
  version = "1.0.0";

  bookSource = ./information-retrieval.tar.gz;
  pySources = [
    ./process_book_html.py
    ./epub.py
    ./cache.py
  ];

  srcs = [
    bookSource
  ] ++ pySources;

  unpackPhase =
    ''
      unpackFile $bookSource
      for fn in $pySources
      do
        cp "$fn" "$(stripHash "$fn")"
      done
    '';

  postPatch =
    ''
      patchShebangs *.py
    '';

  nativeBuildInputs = [
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

  dontConfigure = true;
  buildPhase =
    ''
      ./process_book_html.py
      ./epub.py
      mkdir $out
      mv information-retrieval.epub $out/
    '';

  doCheck = true;
  checkPhase =
    ''
      epubcheck information-retrieval.epub
    '';
}
