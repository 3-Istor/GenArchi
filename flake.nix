{
  description = "GenArchi : environnement de travail (NixOS et toute machine avec Nix)";

  # Branche stable de nixpkgs. flake.lock fige la révision exacte.
  inputs.nixpkgs.url = "git+https://github.com/NixOS/nixpkgs?ref=nixos-26.05&shallow=1";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          packages = with pkgs; [
            opentofu
            tflint
            python313
            uv
            ansible
            (google-cloud-sdk.withExtraComponents [ google-cloud-sdk.components.cloud-firestore-emulator google-cloud-sdk.components.pubsub-emulator ])
            k6
            shellcheck
            jq
            gnumake
            git
            openssh
            docker-compose
          ];

          # uv utilise le Python de Nix au lieu d'en télécharger un.
          UV_PYTHON = "${pkgs.python313}/bin/python3";
          UV_PYTHON_DOWNLOADS = "never";
          # Les wheels manylinux (grpcio, psycopg) cherchent libstdc++ et zlib : on les fournit.
          LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ];

          shellHook = ''
            echo "GenArchi : $(tofu version | head -1), $(python3 --version), uv $(uv --version | cut -d' ' -f2). 'make help' pour commencer."
          '';
        };
      });
    };
}
