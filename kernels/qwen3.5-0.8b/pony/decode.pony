// decode.pony — Single-token decode orchestration for Qwen3.5 0.8B.
//
// Walks all 24 layers in the hybrid (full + linear) schedule via the batched
// forward-layer API.  Buffers are host-owned and reused across calls.
//
// Build: ponyc --path . --output ../build .

actor DecodeOrchestrator
  let _engine: PhenoEngine tag
  var _position: U32 = 0
  var _current_token: I32 = 0

  new create(engine: PhenoEngine tag) =>
    _engine = engine
    _current_token = 0

  be init_token(token_id: I32) =>
    _current_token = token_id

  be decode_step(
    weights: Pointer[U8] tag,
    hidden_buf: Pointer[U8] tag,
    kv_cache: Pointer[U8] tag,
    lin_state: Pointer[U8] tag,
    scratch: Pointer[U8] tag,
    scratch_argmax: Pointer[U8] tag,
    respond: {(I32, U32)} val)
  =>
    """Run one decode step: embed -> 24 layers -> sample -> next token."""
    // Embedding lookup: copy embed row for current token into hidden_buf.
    // weights layout: embed[V*H] then layer_weights[N_LAYERS * W_PER_LAYER].
    let row_bytes = Qwen35.hidden_size().usize() * 2  // fp16 = 2 bytes
    let embed_offset = _current_token.usize() * row_bytes
    let embed_ptr = weights.offset(embed_offset)

    // memcpy embed_row -> hidden_buf (Qwen35.hidden_size() * 2 bytes)
    @memcpy[Pointer[U8]](hidden_buf, embed_ptr, row_bytes.usize())

    // Walk all 24 layers.
    var layer: USize = 0
    while layer < Qwen35.num_hidden_layers() do
      let is_full = Qwen35.layer_is_full(layer)
      let rc = @pheno_engine_forward_layer[I32](
        _engine,
        layer.u32(), 1, 1,
        hidden_buf, hidden_buf,
        weights, scratch)
      if rc != Status.ok() then
        respond(-1, _position)
        return
      end
      // is_full: attention path differentiation is a kernel-engine concern.
      None
      layer = layer + 1
    end

    // Sample next token via fused argmax + temperature.
    var next: I32 = 0
    let rc2 = @kernel_engine_sampling[I32](
      _engine, hidden_buf, addressof next, scratch_argmax,
      1, 1.0, 0)
    if rc2 == Status.ok() then
      _current_token = next
      _position = _position + 1
      respond(next, _position)
    else
      respond(-1, _position)
    end