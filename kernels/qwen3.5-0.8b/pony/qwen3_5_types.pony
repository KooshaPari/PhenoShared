// qwen3_5_types.pony — Pony type definitions for the Qwen3.5 0.8B kernel engine.
//
// Mirrors the arch.yaml constants and the C header in include/qwen3_5.h.
// All size, count, and layout constants are compile-time primitives so the
// Pony compiler can fold index expressions and encode static bounds checks.
//
// Build: ponyc --path . --output ../build qwen3_5_types.pony

primitive Qwen35
  // Model dimensions.
  fun hidden_size():                USize => 1024
  fun intermediate_size():          USize => 6144
  fun vocab_size():                 USize => 248320
  fun num_hidden_layers():          USize => 24
  fun full_head_dim():              USize => 256
  fun full_query_heads():           USize => 8
  fun full_kv_heads():              USize => 4
  fun partial_rotary_factor():      F32   => 0.25
  fun rot_dim():                    USize => 64
  fun rope_theta():                 F64   => 1_000_000.0
  fun linear_key_heads():           USize => 16
  fun linear_key_head_dim():        USize => 128
  fun linear_value_heads():         USize => 8
  fun linear_value_head_dim():      USize => 128
  fun linear_conv_kernel():         USize => 4
  fun full_qkv_dim():               USize => 8 * 256 * 3  // query_heads * head_dim * 3 (q/k/v)
  fun linear_qkv_dim():             USize => 3 * 16 * 128  // 3 * key_heads * key_head_dim
  fun rope_sections():              (USize, USize, USize) => (16, 24, 24)
  fun eps():                        F32   => 1e-6

  // Hybrid schedule: index -> true = full attention, false = linear.
  fun layer_is_full(index: USize): Bool =>
    (index % 4) == 0

  fun num_full_layers(): USize =>
    var n: USize = 0
    var i: USize = 0
    while i < num_hidden_layers() do
      if layer_is_full(i) then n = n + 1 end
      i = i + 1
    end
    n

  fun num_linear_layers(): USize =>
    num_hidden_layers() - num_full_layers()
