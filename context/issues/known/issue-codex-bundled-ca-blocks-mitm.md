# Issue: Codex Bundled CA Prevents MITM Traffic Capture

## Summary

The codex CLI binary (codex-cli v0.98.0) uses Rust's `reqwest` with the `rustls-tls` feature, which bundles Mozilla's root CA certificates at compile time via the `webpki-roots` crate. This makes it impossible to inject a custom CA (e.g., mitmproxy's) at runtime, blocking HTTPS MITM interception for traffic analysis.

## Affected Component

`extern/tracked/codex/codex-rs/backend-client/Cargo.toml` (line 15):
```toml
reqwest = { version = "0.12", default-features = false, features = ["json", "rustls-tls"] }
```

The `rustls-tls` feature is an alias for `rustls-tls-webpki-roots`, which compiles ~150 public CAs into the binary. The alternative feature `rustls-tls-native-roots` would read the system cert store at runtime instead.

## Client Construction

`extern/tracked/codex/codex-rs/core/src/default_client.rs` (line 195):
```rust
let mut builder = reqwest::Client::builder()
    .user_agent(ua)
    .default_headers(headers);
```

No `.add_root_certificate()`, no `.danger_accept_invalid_certs()`, no TLS customization. The TLS trust behavior is entirely determined by the Cargo feature flag at compile time.

## What Doesn't Work

| Approach | Why it fails |
|----------|-------------|
| `NODE_EXTRA_CA_CERTS` | Codex is Rust, not Node.js |
| `SSL_CERT_FILE` | `rustls-tls` ignores system cert env vars |
| `SSLKEYLOGFILE` | Not enabled in this build |
| `REQUESTS_CA_BUNDLE` | Python-specific, irrelevant |
| mitmproxy upstream proxy | TLS handshake fails: `tlsv1 alert unknown ca` |
| `chatgpt_base_url` config | Only controls auxiliary features, not the API endpoint |

## What Would Work

1. **Rebuild from source** with `rustls-tls-native-roots` instead of `rustls-tls`, then add mitmproxy CA to system cert store.
2. **Override the model provider's `base_url`** in codex config to point to a local HTTP reverse proxy (needs investigation — the provider config structure for the built-in "openai" provider may not be overridable).
3. **Use a custom model provider** (e.g., `openai-custom` with `OPENAI_API_KEY` and a custom `base_url` pointing to a local reverse proxy over HTTP).

## Observed Behavior

mitmproxy log when codex connects through it:
```
Client TLS handshake failed. The client does not trust the proxy's
certificate for chatgpt.com (tlsv1 alert unknown ca)
```

## Codex Traffic Channels

The codex binary has **multiple independent traffic channels**, each with its own URL configuration:

```
┌─────────────────────────────────────────────────────────┐
│                 Codex Traffic Channels                   │
├──────────────────┬──────────────────────────────────────┤
│ Channel          │ URL Source                           │
├──────────────────┼──────────────────────────────────────┤
│ Model API        │ OPENAI_BASE_URL env var, or          │
│ (/responses)     │ provider base_url in config.toml     │
│                  │ Default: api.openai.com/v1 (API key) │
│                  │   or chatgpt.com/backend-api/codex   │
│                  │   (ChatGPT auth)                     │
├──────────────────┼──────────────────────────────────────┤
│ Backend-Client   │ chatgpt_base_url in config.toml      │
│ (rate limits,    │ Default: chatgpt.com/backend-api/    │
│  tasks, usage)   │                                      │
├──────────────────┼──────────────────────────────────────┤
│ Analytics        │ chatgpt_base_url in config.toml      │
│ (events)         │ Default: chatgpt.com/backend-api/    │
├──────────────────┼──────────────────────────────────────┤
│ Remote Skills    │ chatgpt_base_url in config.toml      │
│ (hazelnuts)      │ Strips /backend-api, uses             │
│                  │ /public-api/hazelnuts/                │
├──────────────────┼──────────────────────────────────────┤
│ Direct ChatGPT   │ chatgpt_base_url in config.toml      │
│ (generic backend)│ Default: chatgpt.com/backend-api/    │
├──────────────────┼──────────────────────────────────────┤
│ OAuth Login      │ Hardcoded: auth.openai.com           │
│ (one-time)       │ No override available                │
├──────────────────┼──────────────────────────────────────┤
│ OTEL Telemetry   │ Hardcoded: ab.chatgpt.com            │
│ (Statsig)        │ No override available                │
├──────────────────┼──────────────────────────────────────┤
│ MCP Apps/Skills  │ chatgpt_base_url in config.toml      │
├──────────────────┼──────────────────────────────────────┤
│ Connector URLs   │ Hardcoded: chatgpt.com/apps/...      │
│ (UI links)       │ No override available                │
└──────────────────┴──────────────────────────────────────┘
```

`OPENAI_BASE_URL` only controls the **model API** channel. The `chatgpt_base_url` config field controls backend, analytics, and MCP traffic. Auth and OTEL are hardcoded with no runtime override.

`http://` base URLs are accepted without validation — OSS providers (ollama, lmstudio) default to `http://localhost:{port}/v1`.

## Proposed Solution

### Approach A: No Recompilation (Reverse Proxy)

Bypass TLS entirely by routing codex through local HTTP reverse proxies. No TLS = no CA trust problem.

```
  ┌─────────┐         ┌──────────────────┐         ┌──────────┐
  │  codex  │──HTTP──▶│  127.0.0.1:8080  │──HTTPS─▶│ api.     │
  │         │         │  mitmproxy       │         │ openai   │
  │         │         │  (reverse mode)  │         │ .com     │
  │         │         └──────────────────┘         └──────────┘
  │         │
  │         │         ┌──────────────────┐         ┌──────────┐
  │         │──HTTP──▶│  127.0.0.1:8081  │──HTTPS─▶│ chatgpt  │
  │         │         │  mitmproxy       │         │ .com     │
  │         │         │  (reverse mode)  │         │          │
  └─────────┘         └──────────────────┘         └──────────┘
```

**Step 1 — Start two mitmproxy reverse proxies:**

```bash
# Model API proxy (upstream depends on auth mode)
# For API key mode:
mitmdump --mode reverse:https://api.openai.com/ --listen-port 8080 \
  -w model-api.flow

# For ChatGPT auth mode, use chatgpt.com instead:
# mitmdump --mode reverse:https://chatgpt.com/ --listen-port 8080 ...

# Backend/analytics proxy
mitmdump --mode reverse:https://chatgpt.com/ --listen-port 8081 \
  -w backend.flow
```

**Note:** Do NOT use `--set keep_host_header=true`. Codex sends `Host: 127.0.0.1:PORT` (reqwest auto-derives Host from the request URL). mitmproxy's default behavior in reverse mode rewrites the Host header to match the upstream server, which is what the upstream expects.

**Step 2 — Configure codex:**

```bash
# Set model API base URL
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
```

In `~/.codex/config.toml`:
```toml
chatgpt_base_url = "http://127.0.0.1:8081/backend-api/"
```

**Step 3 — Run codex normally:**
```bash
codex
```

**Coverage:**

| Channel | Captured? | How |
|---------|-----------|-----|
| Model API (`/responses`) | ✅ | `OPENAI_BASE_URL` → `:8080` |
| Backend-client (`/wham/*`) | ✅ | `chatgpt_base_url` → `:8081` |
| Analytics | ✅ | `chatgpt_base_url` → `:8081` |
| MCP Apps/Skills | ✅ | `chatgpt_base_url` → `:8081` |
| Remote Skills (`/public-api/hazelnuts/`) | ✅ | `chatgpt_base_url` → `:8081` |
| Direct ChatGPT | ✅ | `chatgpt_base_url` → `:8081` |
| OAuth Login | ❌ | Hardcoded, one-time only, low-value |
| OTEL Telemetry | ❌ | Hardcoded, no-value for analysis |

**Note:** If using ChatGPT auth mode, both proxies target `chatgpt.com` — can be simplified to a single proxy instance. Also, the model API path is `/backend-api/codex/responses` (not `/v1/responses`), so use `OPENAI_BASE_URL="http://127.0.0.1:8081/backend-api/codex"` instead.

### Approach B: Recompilation (Forward Proxy + System CA)

Change 4 `Cargo.toml` files to use `rustls-tls-native-roots` instead of `rustls-tls`, install mitmproxy CA into system store, then use standard forward proxy.

```
  ┌─────────┐         ┌──────────────────┐         ┌──────────┐
  │  codex  │──HTTP──▶│  127.0.0.1:8080  │──HTTPS─▶│   any    │
  │(rebuilt)│  proxy  │  mitmproxy       │         │ endpoint │
  │         │         │  (forward mode)  │         │          │
  └─────────┘         └──────────────────┘         └──────────┘
```

**Source changes** — replace `rustls-tls` with `rustls-tls-native-roots` in:
- `codex-rs/backend-client/Cargo.toml`
- `codex-rs/rmcp-client/Cargo.toml`
- `codex-rs/otel/Cargo.toml`
- `codex-rs/responses-api-proxy/Cargo.toml`

**Setup:**
```bash
# Install mitmproxy CA
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates

# Rebuild
cd extern/tracked/codex && cargo build --release

# Run mitmproxy as forward proxy
mitmproxy --listen-port 8080

# Run codex
https_proxy=http://127.0.0.1:8080 ./target/release/codex
```

**Coverage:** ALL traffic captured (model API, backend, auth, OTEL).

### Comparison

| | Approach A (Reverse Proxy) | Approach B (Recompile) |
|---|---|---|
| Setup effort | 2 proxy instances + env/config | 4 Cargo.toml edits + CA + rebuild |
| Source changes | None | 4 files |
| Model API traffic | ✅ | ✅ |
| Backend traffic | ✅ | ✅ |
| Auth traffic | ❌ (low-value) | ✅ |
| OTEL telemetry | ❌ (no-value) | ✅ |
| Fragility | Must match auth mode to upstream | Just works |

### Recommendation

**Start with Approach A** — it captures all traffic that matters for API analysis with zero source changes. Fall back to Approach B only if complete coverage of auth/telemetry endpoints is needed.

## Related

- OpenSpec change: `analyze-codex-openai-traffic`
- Design doc: `openspec/changes/analyze-codex-openai-traffic/design.md`
