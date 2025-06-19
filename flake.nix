{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { nixpkgs, utils, ... }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
        {
          devShell = with pkgs; mkShell {
            packages = [
              python312
              uv
            ];

            shellHook = ''
              export PATH="$HOME/.local/share/uv/tools/add-staves/bin:$PATH"
              export UV_PUBLISH_TOKEN=$(1pass vtmc24db6eeruutm6kh5cqwnwy "api token")
            '';
          };
        }
    );
}

