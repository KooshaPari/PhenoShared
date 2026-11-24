import{_ as i,o as a,c as n,ae as l}from"./chunks/framework.BHxsYbCo.js";const o=JSON.parse('{"title":"4SGM Native Process Orchestration - Implementation Plan","description":"","frontmatter":{},"headers":[],"relativePath":"plans/4sgm-native-orchestration-implementation.md","filePath":"plans/4sgm-native-orchestration-implementation.md"}'),p={name:"plans/4sgm-native-orchestration-implementation.md"};function t(h,s,e,k,r,E){return a(),n("div",null,[...s[0]||(s[0]=[l(`<h1 id="_4sgm-native-process-orchestration-implementation-plan" tabindex="-1">4SGM Native Process Orchestration - Implementation Plan <a class="header-anchor" href="#_4sgm-native-process-orchestration-implementation-plan" aria-label="Permalink to &quot;4SGM Native Process Orchestration - Implementation Plan&quot;">​</a></h1><p><strong>Date</strong>: January 31, 2026 <strong>Phase</strong>: Implementation &amp; Execution <strong>Timeline</strong>: 2-3 days for full implementation and testing</p><hr><h2 id="_1-implementation-roadmap" tabindex="-1">1. Implementation Roadmap <a class="header-anchor" href="#_1-implementation-roadmap" aria-label="Permalink to &quot;1. Implementation Roadmap&quot;">​</a></h2><h3 id="phase-1-foundation-day-1-am" tabindex="-1">Phase 1: Foundation (Day 1 AM) <a class="header-anchor" href="#phase-1-foundation-day-1-am" aria-label="Permalink to &quot;Phase 1: Foundation (Day 1 AM)&quot;">​</a></h3><ul><li>Install and verify native dependencies</li><li>Create Brewfile</li><li>Create setup scripts</li><li>Validate environment</li></ul><h3 id="phase-2-process-orchestration-day-1-pm" tabindex="-1">Phase 2: Process Orchestration (Day 1 PM) <a class="header-anchor" href="#phase-2-process-orchestration-day-1-pm" aria-label="Permalink to &quot;Phase 2: Process Orchestration (Day 1 PM)&quot;">​</a></h3><ul><li>Create process-compose.yaml</li><li>Configure health checks</li><li>Set up logging infrastructure</li><li>Test service startup order</li></ul><h3 id="phase-3-api-gateway-day-2-am" tabindex="-1">Phase 3: API Gateway (Day 2 AM) <a class="header-anchor" href="#phase-3-api-gateway-day-2-am" aria-label="Permalink to &quot;Phase 3: API Gateway (Day 2 AM)&quot;">​</a></h3><ul><li>Create Caddyfile</li><li>Configure reverse proxy</li><li>Set up development routing</li><li>Test API access patterns</li></ul><h3 id="phase-4-development-tooling-day-2-pm" tabindex="-1">Phase 4: Development Tooling (Day 2 PM) <a class="header-anchor" href="#phase-4-development-tooling-day-2-pm" aria-label="Permalink to &quot;Phase 4: Development Tooling (Day 2 PM)&quot;">​</a></h3><ul><li>Create Makefile</li><li>Create CLI wrapper scripts</li><li>Configure IDE integration</li><li>Validate full workflow</li></ul><h3 id="phase-5-testing-documentation-day-3" tabindex="-1">Phase 5: Testing &amp; Documentation (Day 3) <a class="header-anchor" href="#phase-5-testing-documentation-day-3" aria-label="Permalink to &quot;Phase 5: Testing &amp; Documentation (Day 3)&quot;">​</a></h3><ul><li>End-to-end testing</li><li>Failure scenario testing</li><li>Performance benchmarking</li><li>Documentation completion</li></ul><hr><h2 id="_2-detailed-implementation-steps" tabindex="-1">2. Detailed Implementation Steps <a class="header-anchor" href="#_2-detailed-implementation-steps" aria-label="Permalink to &quot;2. Detailed Implementation Steps&quot;">​</a></h2><h3 id="step-1-create-brewfile" tabindex="-1">Step 1: Create Brewfile <a class="header-anchor" href="#step-1-create-brewfile" aria-label="Permalink to &quot;Step 1: Create Brewfile&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/Brewfile</code></p><p><strong>Actions</strong>:</p><ol><li>List all system dependencies</li><li>Specify exact versions where possible</li><li>Include optional development tools</li><li>Add fallback alternatives</li></ol><p><strong>Contents</strong>:</p><div class="language-ruby vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">ruby</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Brewfile - 4SGM Development Dependencies</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Core Databases</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;postgresql@15&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;redis&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Web Server &amp; Reverse Proxy</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;caddy&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Python Environment</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;python@3.10&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;uv&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># CLI Tools</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;just&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # Task runner</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;direnv&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # Environment management</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Development &amp; Debugging</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;watchman&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # File watcher</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;curl&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # HTTP client</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;jq&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # JSON parser</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># System Monitoring</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;btop&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # Better top</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;lnav&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # Log navigator</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Optional: GUI Tools</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">cask </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;pgadmin4&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # PostgreSQL admin</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">cask </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;redis-pro&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # Redis client</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">cask </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;postico2&quot;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # PostgreSQL client (paid)</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Taps for additional packages</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">tap </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;homebrew-community/core&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">tap </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;F1bonacc1/process-compose&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Process Orchestrator</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">brew </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;F1bonacc1/process-compose/process-compose&quot;</span></span></code></pre></div><p><strong>Installation Command</strong>:</p><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">cd</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> /Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">brew</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> bundle</span></span></code></pre></div><h3 id="step-2-environment-setup-script" tabindex="-1">Step 2: Environment Setup Script <a class="header-anchor" href="#step-2-environment-setup-script" aria-label="Permalink to &quot;Step 2: Environment Setup Script&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/scripts/setup-local-dev.sh</code></p><p><strong>Actions</strong>:</p><ol><li>Check for required tools</li><li>Initialize PostgreSQL if needed</li><li>Set up data directory</li><li>Create initial database</li><li>Validate all connections</li></ol><p><strong>Script</strong>:</p><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">#!/bin/bash</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">set</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;🚀 4SGM Local Development Setup&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;=================================&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Color output</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RED</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[0;31m&#39;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[0;32m&#39;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">YELLOW</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[1;33m&#39;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[0m&#39;</span><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"> # No Color</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check prerequisites</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;📋 Checking prerequisites...&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Python</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;"> !</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> command</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -v</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> python3</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> /dev/null; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RED</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✗ Python 3 not found\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    exit</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> 1</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Python 3 found: $(</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">python3</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> --version</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">)\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># PostgreSQL</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;"> !</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> command</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -v</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> psql</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> /dev/null; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">YELLOW</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}⚠ PostgreSQL not found\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;  Install with: brew install postgresql@15&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    exit</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> 1</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ PostgreSQL found: $(</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">psql</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> --version</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">)\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Redis</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;"> !</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> command</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -v</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> redis-cli</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> /dev/null; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">YELLOW</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}⚠ Redis not found\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;  Install with: brew install redis&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    exit</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> 1</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Redis found$(</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">NC}&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"># Check PostgreSQL data directory</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">echo &quot;🗄️</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">  Configuring PostgreSQL...&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">PG_DATA_DIR=&quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">HOME</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}/Library/PostgreSQL/15/data&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if [ ! -d &quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">$PG_DATA_DIR</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot; ]; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo &quot;  Creating PostgreSQL data directory...&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    mkdir -p &quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">$PG_DATA_DIR</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    initdb -D &quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">$PG_DATA_DIR</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot; --username=postgres</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ PostgreSQL data directory initialized\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">else</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ PostgreSQL data directory exists\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Start PostgreSQL if not running</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;🔧 Starting PostgreSQL...&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if pg_isready -U user &amp;&gt; /dev/null; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ PostgreSQL already running\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">else</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    pg_ctl -D &quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">$PG_DATA_DIR</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot; start</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    sleep 2</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ PostgreSQL started\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Create user and database if needed</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;📊 Setting up database...&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if psql -U postgres -lqt | cut -d \\| -f 1 | grep -qw &quot;user&quot;; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Database user exists\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">else</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    createuser -U postgres user -P user 2&gt;/dev/null || true</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Database user created\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if psql -U postgres -lqt | cut -d \\| -f 1 | grep -qw &quot;4sgm&quot;; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Database &#39;4sgm&#39; exists\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">else</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    createdb -U postgres -O user 4sgm</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Database &#39;4sgm&#39; created\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Start Redis if not running</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;⚡ Starting Redis...&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if redis-cli ping &amp;&gt; /dev/null; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Redis already running\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">else</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    redis-server --daemonize yes</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    sleep 1</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Redis started\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Set up Python environment</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;🐍 Setting up Python environment...&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">cd /Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if [ ! -d &quot;.venv&quot; ]; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    python3 -m venv .venv</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Virtual environment created\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">else</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Virtual environment exists\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">source .venv/bin/activate</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Install dependencies</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;📦 Installing dependencies...&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">pip install -q uv</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">uv pip install -e .</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Dependencies installed\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Create logs directory</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">mkdir -p logs</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Logs directory created\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"># Copy .env if needed</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">if [ ! -f &quot;.env&quot; ]; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    if [ -f &quot;.env.example&quot; ]; then</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">        cp .env.example .env</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">        echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">YELLOW</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}⚠ Created .env from template - update with secrets\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">    fi</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo -e &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✅ Setup complete!\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;Next steps:&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;  1. Update .env with your secrets&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;  2. Run: process-compose up&quot;</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">echo &quot;  3. Open: http://localhost:8000/docs&quot;</span></span></code></pre></div><h3 id="step-3-create-process-compose-yaml" tabindex="-1">Step 3: Create process-compose.yaml <a class="header-anchor" href="#step-3-create-process-compose-yaml" aria-label="Permalink to &quot;Step 3: Create process-compose.yaml&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/process-compose.yaml</code></p><p><strong>Key Configuration</strong>:</p><div class="language-yaml vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">yaml</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">version</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&quot;3.0&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">environment</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">  - </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">LOG_DIR=logs</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">  - </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">PYTHONUNBUFFERED=1</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">  - </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">PYTHONPATH=/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">processes</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # ============================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # PHASE 1: Infrastructure (No Dependencies)</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # ============================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">  postgres</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">pg_ctl -D \${HOME}/Library/PostgreSQL/15/data start -w</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    working_dir</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">.</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    is_daemon</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">false</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    env</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">      - </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">POSTGRES_USER=user</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">      - </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">POSTGRES_PASSWORD=password</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">      - </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">POSTGRES_DB=4sgm</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    startup</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      type</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">notify</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      action</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">wait</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">10s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    shutdown</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      signal</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">TERM</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    restart_policy</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      backoff</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">exponential</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      max_restarts</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">3</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      wait_period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">2s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    health</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      exec</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">        command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">pg_isready -U user -d 4sgm</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      initial_delay</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">2s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">3s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    log_configuration</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      no_colors</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">false</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      mode</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">mixed</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      location</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">logs/postgres.log</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">  redis</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">redis-server --port 6379 --loglevel notice</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    working_dir</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">.</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    startup</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      type</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">notify</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      action</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">wait</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    shutdown</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">3s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      signal</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">TERM</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    restart_policy</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      backoff</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">exponential</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      max_restarts</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">3</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      wait_period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">1s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    health</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      exec</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">        command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">redis-cli ping</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      initial_delay</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">1s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">2s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    log_configuration</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      no_colors</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">false</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      mode</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">mixed</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      location</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">logs/redis.log</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # ============================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # PHASE 2: MCP Server (Depends on Infra)</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # ============================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">  mcp_server</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">python -m fastmcp run mcp_server.server:mcp</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    working_dir</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/4sgm</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    env_file</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">../.env</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    depends_on</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      postgres</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">running_ok</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      redis</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">running_ok</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    startup</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      type</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">notify</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      action</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">wait</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">10s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    shutdown</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">3s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      signal</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">TERM</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    restart_policy</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      backoff</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">exponential</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      max_restarts</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">5</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      wait_period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">2s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    log_configuration</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      no_colors</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">false</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      mode</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">mixed</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      location</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">../logs/mcp_server.log</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # ============================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # PHASE 3: FastAPI Backend (Depends on MCP)</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">  # ============================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">  fastapi</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    working_dir</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/4sgm</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    env_file</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">../.env</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    depends_on</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      mcp_server</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">running_ok</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      postgres</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">running_ok</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      redis</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">running_ok</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    startup</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      type</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">notify</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      action</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">wait</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">15s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    shutdown</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      signal</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">TERM</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    restart_policy</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      backoff</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">exponential</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      max_restarts</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">5</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      wait_period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">2s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    health</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      exec</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">        command</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">curl -f http://localhost:8000/health || exit 1</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      initial_delay</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">3s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      period</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">10s</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      timeout</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5s</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">    log_configuration</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      no_colors</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">false</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      mode</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">mixed</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">      location</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">../logs/fastapi.log</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">log_configuration</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">  location</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">logs/orchestrator.log</span></span>
<span class="line"><span style="--shiki-light:#22863A;--shiki-dark:#85E89D;">  level</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">info</span></span></code></pre></div><h3 id="step-4-create-caddyfile" tabindex="-1">Step 4: Create Caddyfile <a class="header-anchor" href="#step-4-create-caddyfile" aria-label="Permalink to &quot;Step 4: Create Caddyfile&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/Caddyfile</code></p><p><strong>Configuration</strong>:</p><div class="language-caddyfile vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">caddyfile</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span># Development environment on port 9000</span></span>
<span class="line"><span>localhost:9000 {</span></span>
<span class="line"><span>    # API routes</span></span>
<span class="line"><span>    handle /api/* {</span></span>
<span class="line"><span>        uri strip_prefix /api</span></span>
<span class="line"><span>        reverse_proxy localhost:8000 {</span></span>
<span class="line"><span>            header_up X-Forwarded-For {http.request.remote}</span></span>
<span class="line"><span>            header_up X-Forwarded-Proto {http.request.proto}</span></span>
<span class="line"><span>        }</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    # Health check endpoint</span></span>
<span class="line"><span>    handle /health {</span></span>
<span class="line"><span>        reverse_proxy localhost:8000</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    # Swagger documentation</span></span>
<span class="line"><span>    handle /docs {</span></span>
<span class="line"><span>        reverse_proxy localhost:8000</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    # ReDoc documentation</span></span>
<span class="line"><span>    handle /redoc {</span></span>
<span class="line"><span>        reverse_proxy localhost:8000</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    # OpenAPI schema</span></span>
<span class="line"><span>    handle /openapi.json {</span></span>
<span class="line"><span>        reverse_proxy localhost:8000</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    # Frontend with fallback</span></span>
<span class="line"><span>    handle {</span></span>
<span class="line"><span>        reverse_proxy localhost:3001 {</span></span>
<span class="line"><span>            policy random_choose</span></span>
<span class="line"><span>        }</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    # Logging</span></span>
<span class="line"><span>    log {</span></span>
<span class="line"><span>        output file logs/caddy.log {</span></span>
<span class="line"><span>            roll_size 100mb</span></span>
<span class="line"><span>            roll_keep 5</span></span>
<span class="line"><span>            roll_keep_for 720h</span></span>
<span class="line"><span>        }</span></span>
<span class="line"><span>        level info</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span>}</span></span>
<span class="line"><span></span></span>
<span class="line"><span># Production-like on port 9001 (single API)</span></span>
<span class="line"><span>localhost:9001 {</span></span>
<span class="line"><span>    reverse_proxy localhost:8000 {</span></span>
<span class="line"><span>        header_up X-Forwarded-For {http.request.remote}</span></span>
<span class="line"><span>        header_up X-Forwarded-Proto {http.request.proto}</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span></span></span>
<span class="line"><span>    log {</span></span>
<span class="line"><span>        output file logs/caddy-prod.log {</span></span>
<span class="line"><span>            roll_size 100mb</span></span>
<span class="line"><span>            roll_keep 5</span></span>
<span class="line"><span>        }</span></span>
<span class="line"><span>        level warn</span></span>
<span class="line"><span>    }</span></span>
<span class="line"><span>}</span></span></code></pre></div><h3 id="step-5-create-makefile" tabindex="-1">Step 5: Create Makefile <a class="header-anchor" href="#step-5-create-makefile" aria-label="Permalink to &quot;Step 5: Create Makefile&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/Makefile</code></p><p><strong>Structure</strong>:</p><div class="language-makefile vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">makefile</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">.PHONY</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: help setup clean start stop logs restart health </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        postgres redis mcp api frontend test lint format </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        docker-start docker-stop database-init</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Default target</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">help</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;4SGM Development Commands&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;=========================&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;Setup &amp; Installation:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make setup           - Initial setup (install deps, init DB)&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make clean           - Clean all artifacts and caches&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;Service Management:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make start           - Start all services via process-compose&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make stop            - Stop all services gracefully&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make restart         - Restart all services&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make logs            - Tail all service logs&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make health          - Check service health&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;Individual Services:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make postgres        - Start PostgreSQL only&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make redis           - Start Redis only&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make mcp             - Start MCP server only&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make api             - Start FastAPI only&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make frontend        - Start React frontend only&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;Development:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make test            - Run tests&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make lint            - Run linting checks&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make format          - Format code&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make database-init   - Initialize database&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;Docker Fallback:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make docker-start    - Start services via Docker Compose&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;  make docker-stop     - Stop Docker services&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Setup &amp; Installation</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">setup</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: .env</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🚀 Setting up 4SGM development environment...&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">bash scripts/setup-local-dev.sh</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;✅ Setup complete!&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">.env</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">if [ -f &quot;.env.example&quot; ]; then </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">		cp .env.example .env; </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">		echo &quot;Created .env from template - update with your secrets&quot;; </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">clean</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🧹 Cleaning...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	rm -rf logs</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	rm -rf __pycache__</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	rm -rf .pytest_cache</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	rm -rf .mypy_cache</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	rm -rf .ruff_cache</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	find . -type d -name __pycache__ -exec rm -rf {} +</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	find . -name &quot;*.pyc&quot; -delete</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;✅ Cleaned!&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Service Management</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">start</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🚀 Starting 4SGM services...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	process-compose up</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">stop</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🛑 Stopping services...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	process-compose down</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">restart</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: stop start</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">logs</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;📋 Tailing service logs...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	process-compose logs -f</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">health</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🏥 Checking service health...&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;PostgreSQL:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">pg_isready -U user -d 4sgm &amp;&amp; echo &quot;  ✓ Running&quot; || echo &quot;  ✗ Not responding&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;Redis:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">redis-cli ping &amp;&amp; echo &quot;  ✓ Running&quot; || echo &quot;  ✗ Not responding&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;FastAPI:&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">curl -s http://localhost:8000/health &amp;&amp; echo &quot;&quot; &amp;&amp; echo &quot;  ✓ Running&quot; || echo &quot;  ✗ Not responding&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Individual Services</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">postgres</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🗄️  Starting PostgreSQL...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	pg_ctl -D </span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">HOME</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">/Library/PostgreSQL/15/data start</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">redis</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;⚡ Starting Redis...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	redis-server --daemonize yes</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">mcp</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🔧 Starting MCP Server...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm &amp;&amp; python -m fastmcp run mcp_server.server:mcp</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">api</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🚀 Starting FastAPI...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm &amp;&amp; python -m uvicorn backend.app:app --reload --port 8000</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">frontend</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🎨 Starting React Frontend...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm/frontend &amp;&amp; npm run dev</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Development Tools</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">test</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🧪 Running tests...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm &amp;&amp; python -m pytest -v</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">lint</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🔍 Linting code...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm &amp;&amp; python -m ruff check .</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">format</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;✨ Formatting code...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm &amp;&amp; python -m black . &amp;&amp; python -m ruff check --fix .</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">database-init</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;📊 Initializing database...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	cd 4sgm &amp;&amp; python -c &quot;from backend.database import init_db; init_db()&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Docker Fallback</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">docker-start</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🐳 Starting Docker Compose...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	docker-compose up -d</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">docker-stop</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">:</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">	@</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">echo &quot;🛑 Stopping Docker Compose...&quot;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">	docker-compose down</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Utility</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># ====================================</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">.PHONY</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">: setup clean start stop restart logs health </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        postgres redis mcp api frontend test lint format </span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">\\</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">        database-init docker-start docker-stop help</span></span></code></pre></div><h3 id="step-6-create-health-check-script" tabindex="-1">Step 6: Create Health Check Script <a class="header-anchor" href="#step-6-create-health-check-script" aria-label="Permalink to &quot;Step 6: Create Health Check Script&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/scripts/health-check.sh</code></p><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;">#!/bin/bash</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Colors</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[0;32m&#39;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RED</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[0;31m&#39;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">YELLOW</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[1;33m&#39;</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">&#39;\\033[0m&#39;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;🏥 4SGM Health Check&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;====================&quot;</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check PostgreSQL</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -n</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;PostgreSQL... &quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> pg_isready</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -U</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> user</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -d</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> 4sgm</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">/dev/null; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Running\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">else</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RED</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✗ Not responding\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check Redis</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -n</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;Redis...      &quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> redis-cli</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ping</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">/dev/null </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">|</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> grep</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -q</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> PONG</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Running\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">else</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RED</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✗ Not responding\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check FastAPI</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -n</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;FastAPI...    &quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> curl</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -s</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> http://localhost:8000/health</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">/dev/null; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Running\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">else</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RED</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✗ Not responding\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check MCP (if available)</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -n</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;MCP Server... &quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">if</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> curl</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -s</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> http://localhost:3000/health</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">/dev/null; </span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">then</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">GREEN</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}✓ Running\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">else</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">    echo</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">YELLOW</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}⚠ Not available\${</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">NC</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">}&quot;</span></span>
<span class="line"><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">fi</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;&quot;</span></span></code></pre></div><h3 id="step-7-update-env-example" tabindex="-1">Step 7: Update .env.example <a class="header-anchor" href="#step-7-update-env-example" aria-label="Permalink to &quot;Step 7: Update .env.example&quot;">​</a></h3><p><strong>Location</strong>: <code>/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/.env.example</code></p><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Service Configuration</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">LOG_LEVEL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">INFO</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">PYTHONUNBUFFERED</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">1</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">ENVIRONMENT</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">development</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Database Configuration</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">DATABASE_URL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">postgresql://user:password@localhost:5432/4sgm</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">POSTGRES_USER</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">user</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">POSTGRES_PASSWORD</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">password</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">POSTGRES_DB</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">4sgm</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">POSTGRES_HOST</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">localhost</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">POSTGRES_PORT</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">5432</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Redis Configuration</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">REDIS_URL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">redis://localhost:6379/0</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># API Keys (obtain from respective services)</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">OPENAI_API_KEY</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">sk-YOUR_KEY_HERE</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">SUPABASE_URL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">https://YOUR_PROJECT.supabase.co</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">SUPABASE_KEY</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">eyJhbGc...</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Service URLs</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">MCP_SERVER_URL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">http://localhost:3000</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">API_BASE_URL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">http://localhost:8000</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">FRONTEND_URL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">http://localhost:3000</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Logging</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">LOG_DIR</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">logs</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">LOG_LEVEL</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">INFO</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Development</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">DEBUG</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">false</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">RELOAD</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">true</span></span></code></pre></div><hr><h2 id="_3-configuration-validation-checklist" tabindex="-1">3. Configuration Validation Checklist <a class="header-anchor" href="#_3-configuration-validation-checklist" aria-label="Permalink to &quot;3. Configuration Validation Checklist&quot;">​</a></h2><h3 id="pre-implementation" tabindex="-1">Pre-Implementation <a class="header-anchor" href="#pre-implementation" aria-label="Permalink to &quot;Pre-Implementation&quot;">​</a></h3><ul><li>[ ] Python 3.10+ installed</li><li>[ ] Homebrew installed</li><li>[ ] Adequate disk space (&gt;5GB)</li><li>[ ] macOS 11+</li></ul><h3 id="installation-phase" tabindex="-1">Installation Phase <a class="header-anchor" href="#installation-phase" aria-label="Permalink to &quot;Installation Phase&quot;">​</a></h3><ul><li>[ ] Brewfile dependencies installed</li><li>[ ] PostgreSQL data directory created</li><li>[ ] Redis configured</li><li>[ ] Python virtual environment created</li><li>[ ] Project dependencies installed</li></ul><h3 id="service-startup" tabindex="-1">Service Startup <a class="header-anchor" href="#service-startup" aria-label="Permalink to &quot;Service Startup&quot;">​</a></h3><ul><li>[ ] PostgreSQL starts and responds to health checks</li><li>[ ] Redis starts and responds to PING</li><li>[ ] MCP server loads 25+ tools</li><li>[ ] FastAPI connects to MCP server</li><li>[ ] Health endpoints return 200 OK</li></ul><h3 id="integration-testing" tabindex="-1">Integration Testing <a class="header-anchor" href="#integration-testing" aria-label="Permalink to &quot;Integration Testing&quot;">​</a></h3><ul><li>[ ] Frontend connects to API</li><li>[ ] Chat endpoint responds</li><li>[ ] Streaming works (SSE)</li><li>[ ] MCP tools are callable</li><li>[ ] Database queries work</li><li>[ ] Cache operations work</li></ul><hr><h2 id="_4-manual-service-testing" tabindex="-1">4. Manual Service Testing <a class="header-anchor" href="#_4-manual-service-testing" aria-label="Permalink to &quot;4. Manual Service Testing&quot;">​</a></h2><h3 id="test-postgresql" tabindex="-1">Test PostgreSQL <a class="header-anchor" href="#test-postgresql" aria-label="Permalink to &quot;Test PostgreSQL&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Start PostgreSQL</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">pg_ctl</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -D</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> \${HOME}</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">/Library/PostgreSQL/15/data</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> start</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Test connection</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">psql</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -U</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> user</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -d</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> 4sgm</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -c</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;SELECT 1&quot;</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check version</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">psql</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> --version</span></span></code></pre></div><h3 id="test-redis" tabindex="-1">Test Redis <a class="header-anchor" href="#test-redis" aria-label="Permalink to &quot;Test Redis&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Start Redis</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">redis-server</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> --daemonize</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> yes</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Test connection</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">redis-cli</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ping</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Test data</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">redis-cli</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> SET</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> test</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;Hello&quot;</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> &amp;&amp; </span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">redis-cli</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> GET</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> test</span></span></code></pre></div><h3 id="test-mcp-server" tabindex="-1">Test MCP Server <a class="header-anchor" href="#test-mcp-server" aria-label="Permalink to &quot;Test MCP Server&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">cd</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> /Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/4sgm</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">python</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -m</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> fastmcp</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> run</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> mcp_server.server:mcp</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Should show: &quot;Serving MCP on stdio&quot; or similar</span></span></code></pre></div><h3 id="test-fastapi" tabindex="-1">Test FastAPI <a class="header-anchor" href="#test-fastapi" aria-label="Permalink to &quot;Test FastAPI&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">cd</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> /Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm/4sgm</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">python</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -m</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> uvicorn</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> backend.app:app</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> --port</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> 8000</span></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Should show: &quot;Uvicorn running on http://0.0.0.0:8000&quot;</span></span></code></pre></div><h3 id="test-integration" tabindex="-1">Test Integration <a class="header-anchor" href="#test-integration" aria-label="Permalink to &quot;Test Integration&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Health check</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">curl</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> http://localhost:8000/health</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># List tools</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">curl</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> http://localhost:8000/tools</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Chat endpoint</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">curl</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -X</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> POST</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> http://localhost:8000/chat</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> \\</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">  -H</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;Content-Type: application/json&quot;</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> \\</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">  -d</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &#39;{&quot;text&quot;: &quot;Hello&quot;}&#39;</span></span></code></pre></div><hr><h2 id="_5-troubleshooting-guide" tabindex="-1">5. Troubleshooting Guide <a class="header-anchor" href="#_5-troubleshooting-guide" aria-label="Permalink to &quot;5. Troubleshooting Guide&quot;">​</a></h2><h3 id="postgresql-won-t-start" tabindex="-1">PostgreSQL Won&#39;t Start <a class="header-anchor" href="#postgresql-won-t-start" aria-label="Permalink to &quot;PostgreSQL Won&#39;t Start&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check if already running</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">pg_isready</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check logs</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">tail</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -20</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ~/Library/PostgreSQL/15/data/postgresql.log</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Try to start with more info</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">pg_ctl</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -D</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ~/Library/PostgreSQL/15/data</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> start</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -l</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> pglog.txt</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Reset if corrupted</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">pg_ctl</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -D</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ~/Library/PostgreSQL/15/data</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> stop</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">rm</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -rf</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ~/Library/PostgreSQL/15/data/</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">*</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">initdb</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -D</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> ~/Library/PostgreSQL/15/data</span></span></code></pre></div><h3 id="port-already-in-use" tabindex="-1">Port Already in Use <a class="header-anchor" href="#port-already-in-use" aria-label="Permalink to &quot;Port Already in Use&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Find what&#39;s using port 8000</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">lsof</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -i</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> :8000</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Find what&#39;s using port 5432</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">lsof</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -i</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> :5432</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Kill process (use PID from above)</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">kill</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -9</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;"> &lt;</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">PI</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">D</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">&gt;</span></span></code></pre></div><h3 id="python-import-errors" tabindex="-1">Python Import Errors <a class="header-anchor" href="#python-import-errors" aria-label="Permalink to &quot;Python Import Errors&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Reset virtual environment</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">rm</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -rf</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> .venv</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">python3</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -m</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> venv</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> .venv</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">source</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> .venv/bin/activate</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">pip</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> install</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -e</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> .</span></span></code></pre></div><h3 id="mcp-server-won-t-start" tabindex="-1">MCP Server Won&#39;t Start <a class="header-anchor" href="#mcp-server-won-t-start" aria-label="Permalink to &quot;MCP Server Won&#39;t Start&quot;">​</a></h3><div class="language-bash vp-adaptive-theme"><button title="Copy Code" class="copy"></button><span class="lang">bash</span><pre class="shiki shiki-themes github-light github-dark vp-code" tabindex="0"><code><span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check PYTHONPATH</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">echo</span><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;"> $PYTHONPATH</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Try manual startup</span></span>
<span class="line"><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;">cd</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> 4sgm</span></span>
<span class="line"><span style="--shiki-light:#24292E;--shiki-dark:#E1E4E8;">PYTHONPATH</span><span style="--shiki-light:#D73A49;--shiki-dark:#F97583;">=</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">/Users/kooshapari/temp-PRODVERCEL/485/kush/4sgm</span><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;"> \\</span></span>
<span class="line"><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;">  python</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -m</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> fastmcp</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> run</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> mcp_server.server:mcp</span></span>
<span class="line"></span>
<span class="line"><span style="--shiki-light:#6A737D;--shiki-dark:#6A737D;"># Check tool definitions</span></span>
<span class="line"><span style="--shiki-light:#6F42C1;--shiki-dark:#B392F0;">python</span><span style="--shiki-light:#005CC5;--shiki-dark:#79B8FF;"> -c</span><span style="--shiki-light:#032F62;--shiki-dark:#9ECBFF;"> &quot;from mcp_server.server import mcp; print(dir(mcp))&quot;</span></span></code></pre></div><hr><h2 id="_6-performance-optimization-tips" tabindex="-1">6. Performance Optimization Tips <a class="header-anchor" href="#_6-performance-optimization-tips" aria-label="Permalink to &quot;6. Performance Optimization Tips&quot;">​</a></h2><h3 id="reduce-memory-usage" tabindex="-1">Reduce Memory Usage <a class="header-anchor" href="#reduce-memory-usage" aria-label="Permalink to &quot;Reduce Memory Usage&quot;">​</a></h3><ul><li>Disable unused tools in MCP server</li><li>Use connection pooling for database</li><li>Enable Redis compression</li></ul><h3 id="improve-startup-time" tabindex="-1">Improve Startup Time <a class="header-anchor" href="#improve-startup-time" aria-label="Permalink to &quot;Improve Startup Time&quot;">​</a></h3><ul><li>Pre-warm Python bytecode</li><li>Use hypercorn instead of uvicorn</li><li>Parallelize service startup</li></ul><h3 id="network-optimization" tabindex="-1">Network Optimization <a class="header-anchor" href="#network-optimization" aria-label="Permalink to &quot;Network Optimization&quot;">​</a></h3><ul><li>Use Unix sockets for local connections</li><li>Enable HTTP/2 in Caddy</li><li>Reduce verbose logging</li></ul><hr><h2 id="_7-deliverables-checklist" tabindex="-1">7. Deliverables Checklist <a class="header-anchor" href="#_7-deliverables-checklist" aria-label="Permalink to &quot;7. Deliverables Checklist&quot;">​</a></h2><ul><li>[ ] <code>Brewfile</code> - Dependency declaration</li><li>[ ] <code>process-compose.yaml</code> - Process orchestration</li><li>[ ] <code>Caddyfile</code> - Reverse proxy configuration</li><li>[ ] <code>Makefile</code> - Development commands</li><li>[ ] <code>scripts/setup-local-dev.sh</code> - Setup automation</li><li>[ ] <code>scripts/health-check.sh</code> - Health monitoring</li><li>[ ] Updated <code>.env.example</code> - Configuration template</li><li>[ ] Documentation - Local development guide</li><li>[ ] Test suite passing</li><li>[ ] Performance benchmarks</li></ul><hr><h2 id="_8-timeline-milestones" tabindex="-1">8. Timeline &amp; Milestones <a class="header-anchor" href="#_8-timeline-milestones" aria-label="Permalink to &quot;8. Timeline &amp; Milestones&quot;">​</a></h2><table tabindex="0"><thead><tr><th>Milestone</th><th>Timeline</th><th>Status</th></tr></thead><tbody><tr><td>Environment setup</td><td>Day 1 AM</td><td>Pending</td></tr><tr><td>Brewfile creation</td><td>Day 1 AM</td><td>Pending</td></tr><tr><td>process-compose configuration</td><td>Day 1 PM</td><td>Pending</td></tr><tr><td>Initial testing</td><td>Day 1 PM</td><td>Pending</td></tr><tr><td>Caddyfile &amp; reverse proxy</td><td>Day 2 AM</td><td>Pending</td></tr><tr><td>Makefile &amp; scripts</td><td>Day 2 AM</td><td>Pending</td></tr><tr><td>Full integration testing</td><td>Day 2 PM</td><td>Pending</td></tr><tr><td>Performance benchmarking</td><td>Day 3</td><td>Pending</td></tr><tr><td>Documentation finalization</td><td>Day 3</td><td>Pending</td></tr></tbody></table><hr><h2 id="_9-success-metrics" tabindex="-1">9. Success Metrics <a class="header-anchor" href="#_9-success-metrics" aria-label="Permalink to &quot;9. Success Metrics&quot;">​</a></h2><ul><li>All 5 services start in &lt;15 seconds</li><li>&lt;450MB total memory usage</li><li>&lt;1ms latency between services</li><li>100% health check pass rate</li><li>0 startup failures in 10 consecutive runs</li><li>Full test suite passing</li><li>Documentation complete and accurate</li></ul><hr><p><strong>Document Version</strong>: 1.0 <strong>Status</strong>: Ready for Implementation <strong>Last Updated</strong>: January 31, 2026</p>`,99)])])}const g=i(p,[["render",t]]);export{o as __pageData,g as default};
