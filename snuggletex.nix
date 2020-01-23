{
  pkgs ? import <nixpkgs> {},
}:
with pkgs;
stdenv.mkDerivation rec {
  name = "SnuggleTeX";
  version = "1.2.2";

  # From sourceforge: https://www2.ph.ed.ac.uk/snuggletex/documentation/getting-snuggletex.html
  src = ./snuggletex-1.2.2-full.zip;
  wrapper = ./snuggletex.sh;

  nativeBuildInputs = with pkgs; [
    unzip
  ];

  java = adoptopenjdk-bin;
  buildInputs = with pkgs; [
    java
  ];

  dontConfigure = true;
  dontBuild = true;
  installPhase =
    ''
      mkdir -p $out
      rm -rf src
      mv bin $out/
      mv README.txt LICENSE.txt $out/
      cp $wrapper $out/bin/snuggletex
      chmod +x $out/bin/snuggletex
      substituteAllInPlace $out/bin/snuggletex
    '';
}
