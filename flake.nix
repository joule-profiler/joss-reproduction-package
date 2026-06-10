{
  description = "Reproducible experiment environment for Grid'5000 experiments";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
  
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
  in {
    devShells.${system}.default = pkgs.mkShell {
      packages = with pkgs; [
        
        git
        vim
        pkg-config
        openssl
        openssl.dev
        stdenv.cc.cc.lib

        linuxPackages_6_12.perf
        stress-ng
        
        rustup
        rustc

        python3
        uv
      ];

      shellHook = ''
            mkdir -p $(pwd)/.libs

            # NVML
            NVML_LIB=$(find /usr/lib/x86_64-linux-gnu -name "libnvidia-ml.so.*.*" 2>/dev/null | head -1)
            [ -n "$NVML_LIB" ] && ln -sf "$NVML_LIB" $(pwd)/.libs/libnvidia-ml.so.1 && ln -sf "$NVML_LIB" $(pwd)/.libs/libnvidia-ml.so

            # CUDA
            CUDA_LIB=$(find /usr/lib/x86_64-linux-gnu -name "libcuda.so.*.*" 2>/dev/null | head -1)
            [ -n "$CUDA_LIB" ] && ln -sf "$CUDA_LIB" $(pwd)/.libs/libcuda.so.1 && ln -sf "$CUDA_LIB" $(pwd)/.libs/libcuda.so

            # libstdc++
            STDCPP_LIB=$(find /usr/lib/x86_64-linux-gnu -name "libstdc++.so.6" 2>/dev/null | head -1)
            [ -n "$STDCPP_LIB" ] && ln -sf "$STDCPP_LIB" $(pwd)/.libs/libstdc++.so.6

            export LD_LIBRARY_PATH=$(pwd)/.libs:$LD_LIBRARY_PATH
            export PATH=$PATH:''${CARGO_HOME:-~/.cargo}/bin

            echo "  Grid'5000 dev shell"
            echo "  -------------------"
            echo "  rustc   : $(rustc --version)"
            echo "  python  : $(python3 --version)"
            echo "  uv      : $(uv --version)"
        '';
    };
  };
}