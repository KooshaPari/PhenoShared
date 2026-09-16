// bench.pony — Kernel benchmark actor.
//
// Runs a warm-up then measures decode-step latency with wall-clock timing.
//
// Build: ponyc --path . --output ../build bench.pony

use "time"
use "collections"

actor Main
  new create(env: Env) =>
    env.out.print("qwen3.5-0.8b Pony benchmark — not linked yet (toolchain optional)")
