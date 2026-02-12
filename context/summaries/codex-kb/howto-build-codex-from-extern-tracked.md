# How to build Codex from `extern/tracked/codex`

This guide covers building the vendored Codex checkout at `extern/tracked/codex` in this repository.

## Choose a build path

- Recommended native CLI build: `codex-rs` (Rust, builds the actual `codex` binary).
- Optional JS package build: `codex-cli` (Node package layer used for npm packaging).

## Build `codex-rs` (recommended)

1. Go to the Rust workspace:

```bash
cd extern/tracked/codex/codex-rs
```

2. Install toolchain and native deps with `pixi global` (conda-forge):

```bash
pixi global install --environment codex-build rust just cargo-nextest pkg-config openssl cmake clang libclang
```

3. Confirm versions/components:

```bash
rustc --version
rustfmt --version
cargo clippy --version
just --version
```

4. Build and run:

```bash
cargo build -p codex-cli
cargo run --bin codex -- --help
```

5. Optional quality/test helpers from the repo `justfile`:

```bash
just fmt
just fix -p codex-cli
cargo test -p codex-cli
```

## Build `codex-cli` / npm package path (optional)

Note: in this repo, `codex-cli` is the npm wrapper and packaging layer for native binaries, not the main Rust implementation.

1. Install JS tooling with `pixi global` (prefer Bun):

```bash
pixi global install --environment codex-js nodejs bun
bun --version
node --version
npm --version
```

2. Preferred install path for using Codex from package managers:

```bash
bun install -g @openai/codex
codex --version
```

3. Keep npm fallback instructions available:

```bash
npm install -g @openai/codex
codex --version
```

4. Stage npm package artifacts from vendored source:

```bash
cd extern/tracked/codex
pixi global install --environment codex-js-tools gh zstd
./scripts/stage_npm_packages.py --release-version 0.6.0 --package codex
```

5. If you also stage `codex-sdk`, install `pnpm` (required by the SDK staging path):

```bash
pixi global install --environment codex-js pnpm
pnpm --version
```

## Notes

- Supported platforms for Codex builds are macOS 12+, Ubuntu 20.04+/Debian 10+, or Windows 11 via WSL2.
- The Rust workspace uses a pinned toolchain in `codex-rs/rust-toolchain.toml`, so matching that version avoids drift.
- If you prefer a preconfigured environment, the repo includes a Nix dev shell with `pkg-config`, `openssl`, `cmake`, `clang`, and `libclang`.
- `pixi search` confirms the required build packages are available on conda-forge, so `apt` is generally unnecessary for this build path.
- If you specifically need `rustup` workflows (for example `rustup component add rust-src`), install `rustup` separately; it is not currently listed as a conda-forge package in `pixi search rustup`.
- Host check (this machine): `node`, `npm`, `bun`, `git`, `python3`, `gh`, and `zstd` are present; `pnpm` is currently missing.
- Packaging scripts in `codex-cli/scripts/` call `npm pack` for tarball generation, so npm must remain installed even if Bun is your preferred package manager.

## Sources

- https://github.com/openai/codex/blob/main/docs/install.md
- https://github.com/openai/codex/blob/main/codex-rs/rust-toolchain.toml
- https://github.com/openai/codex/blob/main/flake.nix
- https://github.com/openai/codex/blob/main/codex-cli/README.md
- https://github.com/openai/codex/blob/main/codex-cli/package.json
- https://github.com/openai/codex/blob/main/codex-cli/scripts/build_npm_package.py
- https://github.com/openai/codex/blob/main/codex-cli/scripts/install_native_deps.py
- https://github.com/openai/codex/blob/main/package.json
- https://github.com/openai/codex/blob/main/scripts/stage_npm_packages.py
- https://pixi.sh/latest/reference/cli/pixi/global/install/
- https://pixi.sh/latest/reference/cli/pixi/search/
- https://bun.sh/docs/pm/cli/install
