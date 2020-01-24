{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python37Packages,
}:
with pkgs;
pythonPackages.buildPythonPackage {
  name = "EbookLib-0.17.1";
  src = pkgs.fetchurl {
    url = "https://files.pythonhosted.org/packages/00/38/7d6ab2e569a9165249619d73b7bc6be0e713a899a3bc2513814b6598a84c/EbookLib-0.17.1.tar.gz";
    sha256 = "fe23e22c28050196c68db3e7b13b257bf39426d927cb395c6f2cc13ac11327f1";
  };
  buildInputs = [
    pythonPackages.six
    pythonPackages.lxml
  ];
  meta = with pkgs.stdenv.lib; {
    homepage = https://github.com/aerkalov/ebooklib;
    license = licenses.agpl3;
    description = "Ebook library which can handle EPUB2/EPUB3 and Kindle format";
  };
}
