{
  ## This example flake comes from: 
  ## https://nix-community.github.io/pyproject.nix/use-cases/requirements.html
  ##

  description = "Construct development shell from requirements.txt";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  inputs.pyproject-nix.url = "github:nix-community/pyproject.nix";

  outputs =
    { nixpkgs
    , pyproject-nix
    , ...
    }:
    let
      # Load/parse requirements.txt
      project = pyproject-nix.lib.project.loadRequirementsTxt {
        projectRoot = ./.;
      };

      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      python = pkgs.python3;

      # embit is not currently available in nixpkgs, so we build it here
      embit = pkgs.python3Packages.buildPythonPackage rec {
          pname = "embit";
          version = "0.7.0";
          pyproject = true;
          src = pkgs.python3Packages.fetchPypi {
            inherit pname version;
            hash = "sha256-Pb1CWCtcPkBiPnsq8ClWumAZ9uHKHDNj8nqp+bygM2Y=";
          };
          nativeBuildInputs = [
            pkgs.python3Packages.setuptools
          ];
      };

      # urtools is not currently available in nixpkgs, so we build it here
      urtypes = pkgs.python3Packages.buildPythonPackage rec {
          pname = "urtypes";
          version = "0.7.0";
          pyproject = true;
          src = pkgs.fetchFromGitHub {
            inherit pname version;
            owner = "selfcustody";
            repo = "urtypes";
            rev = "main";
            hash = "sha256-3fNgWeJyg3knvydsVpbDHUlUxkrKnIsps7+kgqt/8Rs=";
          };
          nativeBuildInputs = [
            pkgs.python3Packages.setuptools
          ];
      };

      # dataclasses (old version?)
      dataclasses = pkgs.python3Packages.buildPythonPackage rec {
          pname = "dataclasses";
          version = "0.8";
          pyproject = false;
          src = pkgs.python3Packages.fetchPypi {
            inherit pname version;
            hash = "sha256-hHkGfzQqz5V9yC7EFdNVq17bfnZGuQ3G4v0dlq0ITJc=";
          };
          nativeBuildInputs = [
            pkgs.python3Packages.setuptools
          ];
      };

      # now we build our actual environment
      pythonEnv = pkgs.python3.withPackages (ps: with ps; [
        embit
        urtypes
        dataclasses
        pyzbar
        pillow
        qrcode
        tkinter
        opencv4
        project.renderers.withPackages {inherit python; }
      ]);

    in
    {
      devShells.x86_64-linux.default =
        pkgs.mkShell {
          packages = [
            pkgs.zbar
            pythonEnv
          ];
        };
    };
}