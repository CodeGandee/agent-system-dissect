import torch
import flashinfer

query = torch.randn(32, 128, device="cuda", dtype=torch.float16)
key = torch.randn(2048, 32, 128, device="cuda", dtype=torch.float16)
value = torch.randn(2048, 32, 128, device="cuda", dtype=torch.float16)
output = flashinfer.single_decode_with_kv_cache(query, key, value)
print("smoke-ok", tuple(output.shape), output.dtype)
