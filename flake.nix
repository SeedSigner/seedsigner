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
      lib = pkgs.lib;
      python = pkgs.python3;
      stdenv = pkgs.python311Packages.stdenv;

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

      # dataclasses (this might not be necessary since dataclasses are native to python 3.11 now)
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

      # pyzbar - using https://github.com/enteropositivo/pyzbar.git@a52ff0b2e8ff714ba53bbf6461c89d672a304411#egg=pyzbar
      # by modifying https://github.com/NixOS/nixpkgs/blob/nixos-unstable/pkgs/development/python-modules/pyzbar/default.nix#L48
      pyzbar-seedsigner = pkgs.python3Packages.buildPythonPackage rec {
          pname = "pyzbar";
          version = "0.1.10-ss";
          pyproject = true;
          src = pkgs.fetchFromGitHub {
            inherit pname version;
            owner = "enteropositivo";
            repo = "pyzbar";
            rev = "master";
            hash = "sha256-M51MclbldqTVUffWNRNFDTFweIwK12fpbTYGid1Aa5s=";
          };

          buildInputs = [ pkgs.zbar ];

          nativeBuildInputs = [
            pkgs.python3Packages.setuptools
          ];

          propagatedBuildInputs = with pkgs.python3Packages; [ pillow numpy ];

          # find_library doesn't return an absolute path
          # https://github.com/NixOS/nixpkgs/issues/7307
          postPatch = ''
            substituteInPlace pyzbar/zbar_library.py \
              --replace \
                "find_library('zbar')" \
                '"${lib.getLib pkgs.zbar}/lib/libzbar${stdenv.hostPlatform.extensions.sharedLibrary}"'
          '';
      };

      # now we build our actual environment
      pythonEnv = pkgs.python3.withPackages (ps: with ps; [
        embit
        urtypes
        dataclasses
        pyzbar-seedsigner
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

          shellHook = ''
            export SEEDSIGNER_USE_EMULATOR=true
          '';
        };
    };
}