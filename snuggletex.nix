{
  pkgs ? import <nixpkgs> {},
}:
with pkgs;
stdenv.mkDerivation rec {
  name = "SnuggleTeX";
  version = "1.2.2";

  srcs = [
    (fetchzip {
      # End the url with "#.zip" to signal that it's a zip file.
      # https://github.com/NixOS/nixpkgs/issues/60157
      url = "https://sourceforge.net/projects/snuggletex/files/snuggletex/${version}/snuggletex-${version}-full.zip/download#.zip";
      sha512 = "2km7fnycz911xw70858s14gs2ij8l3pkj0fxmaqbzp9kfnnn8mbr0jn1vp2f4pp5qidp5f0f1iaiq78xncaj845aarx4pw3pi1h64mn";
      extraPostFetch =
        ''
          find -type d -exec chmod 755 {} \;
        '';
    })
    ./snuggletex
  ];
  sourceRoot = ".";

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

      pushd ./source
      rm -rf src
      mv bin $out/
      mv README.txt LICENSE.txt $out/
      popd

      cp ./snuggletex/snuggletex.sh $out/bin/snuggletex
      chmod +x $out/bin/snuggletex
      substituteAllInPlace $out/bin/snuggletex
    '';

  meta = with lib; {
    license = licenses.bsd3;
  };
}
