#!/usr/bin/env python3
"""
Scaffold PhenoDocs landing pages for all active Phenotype public repos.

Generates:
  sites/<slug>-landing/
    ├── package.json
    ├── vercel.json
    ├── data/config.json
    └── index.astro (copied from template)
"""
import json
import os
import shutil
import sys

SITES_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ASTRO = os.path.join(SITES_DIR, "..", "templates", "landing", "index.astro")

# All active public repos on KooshaPari account
# Format: (slug, name, domain, description, tier, language, features, color)
REPOS = [
    # --- Primary repos (active development) ---
    ("byterail", "BytePort", "byteport.phenotype.space",
     "Declarative Go/AWS deployment platform: GitHub repo to running service.",
     2, "Go / Svelte / Rust", ["DMG/.app/.deb packaging", "GitHub release automation", "One-click deploy to AWS", "Declarative infra config"], "#3b82f6"),

    ("phenoinfra", "PhenoInfra", "phenoinfra.phenotype.space",
     "Compute mesh infrastructure-as-code: OCI + Cloudflare + GCP + AWS + Vercel with ADRs, specs, and runbooks.",
     1, "Rust / TOML / YAML", ["28 shared infrakit crates", "Multi-cloud IaC", "Landing page factory", "Vercel auto-deploy"], "#8b5cf6"),

    ("pine", "Pine", "pine.phenotype.space",
     "Wine-equivalent for Phenotype: Windows and cross-platform app compatibility layer.",
     1, "Rust", ["Windows syscall translation", "macOS/Linux adapter scaffolding", "NanoVMS integration", "CI + cargo-deny"], "#059669"),

    # --- Core ecosystem ---
    ("phenotooling", "PhenoTooling", "phenotooling.phenotype.space",
     "Internal tooling monorepo: 97+ Rust crates for CI/CD, agent dispatch, and release governance.",
     1, "Rust / Go / TypeScript", ["97+ workspace crates", "Agent dispatch", "Release governance", "CI/CD pipelines"], "#f59e0b"),

    ("phenoai", "PhenoAI", "phenoai.phenotype.space",
     "Rust agent workspace: router, sidekick, Eidolon runtime, and inference orchestration.",
     2, "Rust", ["LLM routing", "Agent orchestration", "Eidolon runtime", "Multi-provider support"], "#ef4444"),

    ("phenofabric", "PhenoFabric", "phenofabric.phenotype.space",
     "Fabric mesh: capability descriptors, route compiler, failover, trust-root, and multi-tenant fairness.",
     2, "Rust", ["Capability descriptors", "Route compiler", "Failover chains", "Trust-root auth"], "#06b6d4"),

    ("phenoregistry", "PhenoRegistry", "phenoregistry.phenotype.space",
     "Organization registry: master index connecting specs, patterns, and templates across the Phenotype ecosystem.",
     1, "TOML / Markdown", ["Spec index", "Pattern registry", "Template catalog", "Cross-repo links"], "#84cc16"),

    ("phenodesign", "PhenoDesign", "phenodesign.phenotype.space",
     "Design system: tokens, components, and UX standards for all Phenotype surfaces.",
     2, "CSS / TypeScript / Figma", ["Design tokens", "Component library", "UX standards", "Figma integration"], "#ec4899"),

    ("phenogfx", "PhenoGfx", "phenogfx.phenotype.space",
     "GFX SDK: polyglot graphics with Rust voxel substrate and C# terrain and water rendering.",
     2, "Rust / C#", ["Voxel rendering", "Terrain engine", "Water simulation", "GPU shaders"], "#f97316"),

    ("phenomlx", "PhenoMLX", "phenomlx.phenotype.space",
     "MLX inference engine: Rust performance cores, multi-backend routing, and evaluation tooling.",
     2, "Rust / Python", ["MLX backend", "Multi-backend routing", "Eval harness", "Quantization support"], "#a855f7"),

    ("phenolab", "PhenoLab", "phenolab.phenotype.space",
     "Compression stack and RLVR harness: evaluation tooling for quantized inference on consumer GPUs.",
     2, "Rust / Python", ["RLVR harness", "Compression stack", "Consumer GPU eval", "Benchmark suite"], "#14b8a6"),

    # --- Tooling & CLI ---
    ("helioscli", "HeliosCLI", "helioscli.phenotype.space",
     "Multi-runtime AI CLI: unified interface for agent orchestration and model interaction.",
     2, "Rust", ["Agent orchestration", "Model routing", "Multi-runtime support", "Plugin system"], "#7c3aed"),

    ("helioslite", "HeliosLite", "helioslite.phenotype.space",
     "AI pair programmer CLI for Claude, GPT, Gemini, Grok, Deepseek, and 300+ models.",
     2, "Rust", ["300+ model support", "Pair programming mode", "Terminal UI", "Streaming responses"], "#2563eb"),

    ("helioslab", "HeliosLab", "helioslab.phenotype.space",
     "Phenotype research lab: experimental AI tooling and evaluation harnesses.",
     2, "Rust / Python", ["Eval harnesses", "Experimental tooling", "Research workflows", "Benchmark suites"], "#7c3aed"),

    ("sharecli", "ShareCLI", "sharecli.phenotype.space",
     "Rust process/resource runtime: high-concurrency agent workload scheduler.",
     2, "Rust", ["Process scheduling", "Resource management", "Agent workloads", "Concurrency control"], "#0891b2"),

    ("kcode", "KCode", "kcode.phenotype.space",
     "Most RAM-efficient coding harness: Rust-native agent execution runtime.",
     2, "Rust", ["Low memory footprint", "Agent execution", "Rust-native", "Session management"], "#4f46e5"),

    ("khostty", "Khostty", "khostty.phenotype.space",
     "Ghostty terminal fork: GPU-accelerated cross-platform terminal emulator.",
     2, "Rust / Zig", ["GPU rendering", "Cross-platform", "Terminal multiplexer", "Custom shaders"], "#dc2626"),

    ("substrate", "Substrate", "substrate.phenotype.space",
     "AI execution substrate: provider routing across HTTP, CLI, MCP, and A2A interfaces.",
     2, "Rust", ["Provider routing", "MCP protocol", "A2A support", "Multi-interface"], "#0d9488"),

    ("portage", "Portage", "portage.phenotype.space",
     "Harbor framework: agent evaluations and reinforcement learning environments.",
     2, "Rust / Python", ["Agent eval", "RL environments", "Benchmark framework", "Harbor pattern"], "#6366f1"),

    # --- Data & Traceability ---
    ("tracera", "Tracera", "tracera.phenotype.space",
     "Rust traceability infrastructure: audit trails and provenance for agent workflows.",
     2, "Rust", ["Audit trails", "Provenance tracking", "Agent workflow tracing", "Compliance"], "#059669"),

    ("researchledger", "ResearchLedger", "researchledger.phenotype.space",
     "Incubating: local-first research ledger and LLM knowledge base.",
     2, "Rust", ["Local-first storage", "Research ledger", "LLM knowledge base", "Markdown-native"], "#78716c"),

    ("sessionledger", "SessionLedger", "sessionledger.phenotype.space",
     "Incubating: session ledger, viewergate, and live tokio daemon-graph pipeline.",
     2, "Rust", ["Session tracking", "Live daemon graph", "Tokio pipeline", "Viewer gate"], "#a3a3a3"),

    # --- Simulation & Gaming ---
    ("civis", "Civis", "civis.phenotype.space",
     "Civilization simulation engine: deterministic godgame with multi-client protocol.",
     2, "Rust", ["Deterministic sim", "Multi-client protocol", "Godgame engine", "Replay system"], "#16a34a"),

    ("dino", "Dino", "dino.phenotype.space",
     "DINOForge: general-purpose mod platform for AI agents in Unity.",
     2, "C# / Unity", ["Unity mod platform", "AI agent integration", "Mod loader", "Runtime hooking"], "#65a30d"),

    # --- Infrastructure & DevOps ---
    ("agileplus", "AgilePlus", "agileplus.phenotype.space",
     "Spec-driven development framework: governance, cycles, modules, and work packages.",
     1, "Rust / TypeScript", ["Spec-driven dev", "Governance framework", "Cycle management", "Dashboard"], "#fbbf24"),

    ("omniroute", "OmniRoute", "omniroute.phenotype.space",
     "Multi-provider LLM gateway: OpenAI-compatible endpoint with smart routing across 300+ models.",
     2, "TypeScript", ["300+ model routing", "OpenAI-compatible", "Load balancing", "Failover"], "#22d3ee"),

    # --- Special Purpose ---
    ("melosviz", "Melosviz", "melosviz.phenotype.space",
     "Music-to-visual toolkit: FastAPI backend, Tauri desktop, and Python + Rust SDKs.",
     2, "Python / Rust / TypeScript", ["Music analysis", "Visual generation", "Tauri desktop", "Dual SDK"], "#e879f9"),

    ("civicwarfare", "CivicWarfare", "civicwarfare.phenotype.space",
     "Cities: Skylines II infrastructure survival mod: docs and changelog.",
     3, "C# / Unity", ["Cities: Skylines II mod", "Infrastructure survival", "Gameplay systems", "Mod docs"], "#facc15"),
]


def generate_landing(slug, name, domain, description, tier, language, features, color):
    """Generate a complete landing page directory."""
    landing_dir = os.path.join(SITES_DIR, f"{slug}-landing")

    if os.path.exists(landing_dir):
        print(f"  SKIP  {slug}-landing (already exists)")
        return False

    # Create proper Astro structure
    pages_dir = os.path.join(landing_dir, "src", "pages")
    data_dir = os.path.join(landing_dir, "data")
    os.makedirs(pages_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    # config.json
    config = {
        "name": name,
        "slug": slug,
        "tagline": description.split(".")[0] + ".",
        "domain": domain,
        "color": color,
        "description": description,
        "tier": tier,
        "repo": f"KooshaPari/{name}",
        "language": language,
        "license": "MIT",
        "status": "active",
        "features": features,
        "links": {
            "github": f"https://github.com/KooshaPari/{name}",
            "docs": f"https://{domain}/docs",
            "releases": f"https://github.com/KooshaPari/{name}/releases"
        }
    }
    with open(os.path.join(data_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)

    # package.json
    pkg = {
        "name": f"{slug}-landing",
        "version": "0.1.0",
        "private": True,
        "type": "module",
        "description": f"{name} landing page ({domain})",
        "scripts": {
            "dev": "astro dev",
            "build": "astro build",
            "preview": "astro preview",
            "test": "vitest run",
            "test:watch": "vitest"
        },
        "dependencies": {
            "@astrojs/check": "^0.9.4",
            "@types/node": "^24.10.1",
            "astro": "^7.2.2",
            "@tailwindcss/vite": "^4.0.0",
            "tailwindcss": "^4.0.0",
            "typescript": "^6.0.3"
        },
        "devDependencies": {
            "vitest": "^4.1.5"
        }
    }
    with open(os.path.join(landing_dir, "package.json"), "w") as f:
        json.dump(pkg, f, indent=2)

    # vercel.json
    with open(os.path.join(landing_dir, "vercel.json"), "w") as f:
        json.dump({"framework": "astro", "outputDirectory": "dist"}, f)

    # astro.config.mjs
    with open(os.path.join(landing_dir, "astro.config.mjs"), "w") as f:
        f.write(f"""// @ts-check
import {{ defineConfig }} from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({{
  site: 'https://{domain}',
  vite: {{
    plugins: [tailwindcss()],
  }},
}});
""")

    # tsconfig.json
    with open(os.path.join(landing_dir, "tsconfig.json"), "w") as f:
        json.dump({
            "extends": "astro/tsconfigs/strict",
            "include": [".astro/types.d.ts", "**/*"],
            "exclude": ["dist"],
            "compilerOptions": {
                "resolveJsonModule": True,
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "types": ["astro/client", "node"]
            }
        }, f, indent=2)

    # src/env.d.ts
    with open(os.path.join(pages_dir, "..", "env.d.ts"), "w") as f:
        f.write('/// <reference types="astro/client" />\n')

    # Copy index.astro to src/pages/
    if os.path.exists(TEMPLATE_ASTRO):
        # Fix the import path for standalone sites
        with open(TEMPLATE_ASTRO, "r") as f:
            content = f.read()
        content = content.replace("../../data/config.json", "../../data/config.json")
        with open(os.path.join(pages_dir, "index.astro"), "w") as f:
            f.write(content)
    else:
        print(f"  WARN  Template not found at {TEMPLATE_ASTRO}")

    print(f"  OK    {slug}-landing -> {domain}")
    return True


def main():
    print("=== PhenoDocs Landing Scaffold ===")
    print(f"Target: {SITES_DIR}")
    print(f"Template: {TEMPLATE_ASTRO}")
    print()

    created = 0
    skipped = 0
    for repo in REPOS:
        result = generate_landing(*repo)
        if result:
            created += 1
        else:
            skipped += 1

    print(f"\nDone: {created} created, {skipped} skipped, {len(REPOS)} total")
    print("\nNext steps:")
    print("  1. cd sites/<slug>-landing && bun install && bun run dev")
    print("  2. Create Vercel project: vercel --yes")
    print("  3. Configure CNAME: <slug>.phenotype.space -> cname.vercel-dns.com")


if __name__ == "__main__":
    main()
