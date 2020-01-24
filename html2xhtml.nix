{
  pkgs ? import <nixpkgs> {},
}:
with pkgs;
stdenv.mkDerivation rec {
  name = "html2xhtml";
  version = "1.3";

  src = fetchurl {
    url = "http://www.it.uc3m.es/jaf/html2xhtml/downloads/html2xhtml-${version}.tar.gz";
    sha512 = "38c0603ijimfag04khr7gfgk4qz6drg8c3fw1kgf3ndkr39zwxhk13i30gg31qn8c62kkh4bm3ysbgw42ajxb3gfaljibvj9pd6q4mc";
  };

  buildInputs = [
    libiconv
  ];

  meta = {
    description = "A free-software converter from HTML to XHTML";
  };
}
