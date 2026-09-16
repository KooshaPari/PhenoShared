"""Task pool generation functions for stock-vs-ours analysis.

Contains the per-suite pool functions (_arc_agi_2_pool, _aime_pool, etc.)
that produce lists of TaskSpec for each benchmark suite.
"""

from __future__ import annotations

import random

from bench.comparison.stock_vs_ours_adapters import DIFFICULTY_MIX
from bench.types import TaskSpec


def _arc_agi_2_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    rng = random.Random("arc-agi-2-arc-2026")
    for i in range(DIFFICULTY_MIX["easy"]):
        size = rng.choice([3, 4, 5])
        out.append(
            TaskSpec(
                task_id=f"arc-easy-{i:02d}",
                suite="arc-agi-2",
                difficulty="easy",
                prompt=f"Input grid {size}x{size} with 1 color swap, output the swapped grid",
                expected="match_grid",
                reference="match_grid",
                metadata={"grid_size": size, "transformation": "color_swap"},
            )
        )
    for i in range(DIFFICULTY_MIX["medium"]):
        size = rng.choice([6, 7, 8])
        out.append(
            TaskSpec(
                task_id=f"arc-med-{i:02d}",
                suite="arc-agi-2",
                difficulty="medium",
                prompt=f"Input grid {size}x{size} with reflection + rotation, output the transformed grid",
                expected="match_grid",
                reference="match_grid",
                metadata={"grid_size": size, "transformation": "reflect_rotate"},
            )
        )
    for i in range(DIFFICULTY_MIX["hard"]):
        size = rng.choice([10, 12, 14])
        out.append(
            TaskSpec(
                task_id=f"arc-hard-{i:02d}",
                suite="arc-agi-2",
                difficulty="hard",
                prompt=f"Input grid {size}x{size} with multi-step transformation (color map + scale), output the result",
                expected="match_grid",
                reference="match_grid",
                metadata={"grid_size": size, "transformation": "multi_step"},
            )
        )
    for i in range(DIFFICULTY_MIX["ultra"]):
        size = rng.choice([16, 20, 24])
        out.append(
            TaskSpec(
                task_id=f"arc-ultra-{i:02d}",
                suite="arc-agi-2",
                difficulty="ultra",
                prompt=f"Input grid {size}x{size} with compositional transformation, output the result",
                expected="match_grid",
                reference="match_grid",
                metadata={"grid_size": size, "transformation": "compositional"},
            )
        )
    return out


def _aime_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    easy_kinds = [
        "Find the smallest positive integer n such that n + 7 is divisible by 12.",
        "Compute 13^2 + 14^2 - 15^2.",
        "How many positive divisors does 360 have?",
        "If f(x) = 3x + 5, find f(f(2)).",
        "What is the remainder when 7^100 is divided by 100?",
    ]
    med_kinds = [
        "A box contains 5 red and 3 blue balls. Two balls are drawn without replacement. Find the probability both are red.",
        "The sum of the first n positive integers is 325. Find n.",
        "A rectangle has perimeter 60 and area 200. Find its diagonal length.",
        "Find all pairs (a, b) of positive integers with a + b = 12 and a*b maximal.",
        "How many 3-digit integers are divisible by both 7 and 11?",
        "A sequence starts 2, 5, 11, 23, ... Each term is one more than twice the previous. Find the 10th term.",
        "In triangle ABC, AB=5, AC=7, BC=8. Find the area of the triangle.",
        "How many distinct ways can the letters of MISSISSIPPI be arranged?",
    ]
    hard_kinds = [
        "Find the smallest positive integer m such that m^2 - m + 41 is divisible by 49.",
        "A circle is inscribed in a right triangle with legs 6 and 8. Find the radius.",
        "For how many integers n in [1, 1000] is phi(n) (Euler's totient) a perfect square?",
        "A polynomial P(x) satisfies P(1)=2, P(2)=5, P(3)=12, P(4)=25. Find P(5).",
        "How many lattice points lie strictly inside the triangle with vertices (0,0), (10,0), (0,10)?",
        "Find the sum of all positive divisors of 2^10 - 1.",
        "A 5x5 grid has 25 cells. How many rectangles (any size) can be formed using grid lines?",
    ]
    ultra_kinds = [
        "Find the number of permutations of (1,2,...,7) where no two consecutive integers are adjacent.",
        "A sphere of radius 5 is inscribed in a cylinder. Find the cylinder's volume.",
        "For how many integers n in [1, 1000] does n divide 2^n - 2?",
        "Find the smallest prime p such that p + 2 and p + 6 are also prime.",
        "The decimal expansion of 1/7 has period 6. What is the 2024th digit after the decimal point?",
    ]
    for i, p in enumerate(easy_kinds):
        out.append(
            TaskSpec(
                task_id=f"aime-easy-{i:02d}",
                suite="aime",
                difficulty="easy",
                prompt=p,
                expected="integer",
                reference="integer",
            )
        )
    for i, p in enumerate(med_kinds):
        out.append(
            TaskSpec(
                task_id=f"aime-med-{i:02d}",
                suite="aime",
                difficulty="medium",
                prompt=p,
                expected="integer",
                reference="integer",
            )
        )
    for i, p in enumerate(hard_kinds):
        out.append(
            TaskSpec(
                task_id=f"aime-hard-{i:02d}",
                suite="aime",
                difficulty="hard",
                prompt=p,
                expected="integer",
                reference="integer",
            )
        )
    for i, p in enumerate(ultra_kinds):
        out.append(
            TaskSpec(
                task_id=f"aime-ultra-{i:02d}",
                suite="aime",
                difficulty="ultra",
                prompt=p,
                expected="integer",
                reference="integer",
            )
        )
    return out


def _livecodebench_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    easy_kinds = [
        "def add(a: int, b: int) -> int: return a + b",
        "def reverse_str(s: str) -> str: return s[::-1]",
        "def is_palindrome(s: str) -> bool: return s == s[::-1]",
        "def factorial(n: int) -> int: return 1 if n<=1 else n*factorial(n-1)",
        "def fibonacci(n: int) -> int: a,b=0,1\nfor _ in range(n): a,b=b,a+b\nreturn a",
    ]
    med_kinds = [
        "def two_sum(nums: list[int], target: int) -> list[int]: seen={}; ... O(n) hashmap",
        "def longest_substring(s: str) -> int: sliding window with char counts",
        "def merge_intervals(intervals: list[list[int]]) -> list[list[int]]: sort by start, merge overlaps",
        "def group_anagrams(strs: list[str]) -> list[list[str]]: sort each, group by tuple",
        "def is_valid_parentheses(s: str) -> bool: stack-based check for ()[]{}",
        "def max_subarray(nums: list[int]) -> int: Kadane's algorithm",
        "def product_except_self(nums: list[int]) -> list[int]: prefix/suffix without division",
        "def rotate_matrix_90(m: list[list[int]]) -> list[list[int]]: zip(*m[::-1])",
    ]
    hard_kinds = [
        "def lru_cache_get(capacity: int) -> callable: implement get/put in O(1) with OrderedDict",
        "def word_ladder(begin: str, end: str, words: list[str]) -> int: BFS over word graph",
        "def serialize_deserialize_tree(root) -> tuple: pre-order traversal with null markers",
        "def min_window_substring(s: str, t: str) -> str: sliding window with need/have",
        "def n_queens(n: int) -> list[list[str]]: backtracking with column/diag sets",
        "def longest_increasing_path(matrix: list[list[int]]) -> int: DFS + memoization",
        "def median_two_sorted(a: list[int], b: list[int]) -> float: binary partition O(log(min(m,n)))",
    ]
    ultra_kinds = [
        "def word_break_ii(s: str, wordDict: list[str]) -> list[str]: DFS with memoized word-break",
        "def shortest_path_grid(grid: list[list[int]]) -> int: 0-1 BFS or Dijkstra with state",
        "def minimum_spanning_tree(n: int, edges: list[tuple]) -> int: Kruskal's algorithm with union-find",
        "def regex_match(s: str, p: str) -> bool: dynamic programming with memoization",
        "def alien_dictionary(words: list[str]) -> str: topological sort over char order",
    ]
    for i, p in enumerate(easy_kinds):
        out.append(
            TaskSpec(
                task_id=f"lcb-easy-{i:02d}",
                suite="livecodebench",
                difficulty="easy",
                prompt=p,
                expected="code",
                reference="code",
            )
        )
    for i, p in enumerate(med_kinds):
        out.append(
            TaskSpec(
                task_id=f"lcb-med-{i:02d}",
                suite="livecodebench",
                difficulty="medium",
                prompt=p,
                expected="code",
                reference="code",
            )
        )
    for i, p in enumerate(hard_kinds):
        out.append(
            TaskSpec(
                task_id=f"lcb-hard-{i:02d}",
                suite="livecodebench",
                difficulty="hard",
                prompt=p,
                expected="code",
                reference="code",
            )
        )
    for i, p in enumerate(ultra_kinds):
        out.append(
            TaskSpec(
                task_id=f"lcb-ultra-{i:02d}",
                suite="livecodebench",
                difficulty="ultra",
                prompt=p,
                expected="code",
                reference="code",
            )
        )
    return out


def _aider_polyglot_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    languages = ["python", "javascript", "go", "rust", "java", "cpp"]
    rng = random.Random("aider-polyglot-2026")
    easy_kinds = [
        "rename a misleadingly named function",
        "add type hints to a public function signature",
        "remove an unused import",
        "fix a typo in a docstring",
        "replace a deprecated API call with its modern equivalent",
    ]
    med_kinds = [
        "refactor a function to handle None inputs without raising",
        "extract a duplicate pattern into a single helper function",
        "convert a sync function to async without breaking the public API",
        "add comprehensive docstrings to a public module",
        "replace manual loops with stdlib functions (e.g. sum/comprehensions)",
        "extract magic numbers into named constants",
        "add input validation with clear error messages",
        "introduce a dataclass for a tuple-of-tuples data shape",
    ]
    hard_kinds = [
        "split a 200-line function into 3 focused functions with clean interfaces",
        "implement a generic retry decorator with exponential backoff",
        "convert imperative state mutations to immutable transformations",
        "introduce dependency injection to decouple a tight coupling",
        "add a property-based test suite alongside the existing unit tests",
        "convert a single-file script into a package with __init__.py exports",
        "implement a streaming parser for a 1GB+ log file",
    ]
    ultra_kinds = [
        "migrate a codebase from one language to another preserving identical behavior",
        "design and implement a plugin system that preserves the existing public API",
        "rewrite a 1500-line module to eliminate a global state mutation pattern",
        "implement a domain-specific query language with parser, AST, and evaluator",
        "design a multi-threaded pipeline with backpressure for 100K events/sec",
    ]
    for i, p in enumerate(easy_kinds):
        out.append(
            TaskSpec(
                task_id=f"ap-easy-{i:02d}",
                suite="aider-polyglot",
                difficulty="easy",
                prompt=f"In repo ({rng.choice(languages)}): {p}",
                expected="diff",
                reference="diff",
                metadata={"language": rng.choice(languages)},
            )
        )
    for i, p in enumerate(med_kinds):
        out.append(
            TaskSpec(
                task_id=f"ap-med-{i:02d}",
                suite="aider-polyglot",
                difficulty="medium",
                prompt=f"In repo ({rng.choice(languages)}): {p}",
                expected="diff",
                reference="diff",
                metadata={"language": rng.choice(languages)},
            )
        )
    for i, p in enumerate(hard_kinds):
        out.append(
            TaskSpec(
                task_id=f"ap-hard-{i:02d}",
                suite="aider-polyglot",
                difficulty="hard",
                prompt=f"In repo ({rng.choice(languages)}): {p}",
                expected="diff",
                reference="diff",
                metadata={"language": rng.choice(languages)},
            )
        )
    for i, p in enumerate(ultra_kinds):
        out.append(
            TaskSpec(
                task_id=f"ap-ultra-{i:02d}",
                suite="aider-polyglot",
                difficulty="ultra",
                prompt=f"In repo ({rng.choice(languages)}): {p}",
                expected="diff",
                reference="diff",
                metadata={"language": rng.choice(languages)},
            )
        )
    return out


def _swe_bench_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    repos = ["pydantic", "fastapi", "httpx", "pydantic-settings", "django", "flask"]
    fix_descriptions = [
        "add a missing import statement",
        "fix a typo in a docstring",
        "rename a misleadingly named function",
        "replace a deprecated API call with its modern equivalent",
        "fix an off-by-one error in a loop",
        "add type hints to a public function signature",
        "remove an unused import",
        "add a missing dependency to requirements.txt",
        "fix a broken assertion in a test",
        "rename a private attribute to a public one",
    ]
    rng = random.Random("swe-bench-2026")
    for i in range(DIFFICULTY_MIX["easy"]):
        out.append(
            TaskSpec(
                task_id=f"swe-easy-{i:02d}",
                suite="swe-bench",
                difficulty="easy",
                prompt=f"In repo {rng.choice(repos)}: {rng.choice(fix_descriptions)}",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    for i in range(DIFFICULTY_MIX["medium"]):
        out.append(
            TaskSpec(
                task_id=f"swe-med-{i:02d}",
                suite="swe-bench",
                difficulty="medium",
                prompt=f"In repo {rng.choice(repos)}: refactor a function to handle None inputs without raising",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    for i in range(DIFFICULTY_MIX["hard"]):
        out.append(
            TaskSpec(
                task_id=f"swe-hard-{i:02d}",
                suite="swe-bench",
                difficulty="hard",
                prompt=f"In repo {rng.choice(repos)}: extract a duplicate pattern into a single helper function",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    for i in range(DIFFICULTY_MIX["ultra"]):
        out.append(
            TaskSpec(
                task_id=f"swe-ultra-{i:02d}",
                suite="swe-bench",
                difficulty="ultra",
                prompt=f"In repo {rng.choice(repos)}: convert a sync function to async without breaking the public API",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    return out


def _swe_bench_pro_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    repos = [
        "fastapi/fastapi",
        "pydantic/pydantic",
        "encode/httpx",
        "tokio-rs/tokio",
        "gin-gonic/gin",
        "spring-projects/spring-boot",
    ]
    rng = random.Random("swe-bench-pro-2026")
    easy_kinds = [
        "Apply a single-line docstring fix across one file.",
        "Update one import statement to its modern equivalent.",
        "Rename a private method to follow naming convention.",
        "Fix one off-by-one error in a list slice.",
        "Replace one deprecated API call with its current equivalent.",
    ]
    med_kinds = [
        "Refactor an internal helper to reduce cyclomatic complexity under 8.",
        "Introduce a new Pydantic model and migrate 3 call sites to use it.",
        "Add a new optional kwarg to a public function with backwards compat.",
        "Extract a duplicated 12-line block into a private helper.",
        "Convert a sync I/O wrapper to async without changing public surface.",
        "Add comprehensive error messages to a parser (8 distinct error paths).",
        "Migrate a from-import to a relative import across 4 files.",
        "Add type narrowing for a Union return in 6 callers.",
    ]
    hard_kinds = [
        "Apply a multi-file refactor that introduces a new abstraction layer.",
        "Migrate from stdlib logging to structured logging with migration shim.",
        "Replace a custom dict-based cache with functools.lru_cache + invalidation hook.",
        "Add a new feature flag (boolean) gated across 4 modules with default-on.",
        "Migrate a public API from callback-based to Promise/Future-based.",
        "Introduce async context managers in 3 files for resource cleanup.",
        "Add a new HTTP middleware with config validation and tests.",
    ]
    ultra_kinds = [
        "Migrate a 5000-line module to a new dependency-injected architecture.",
        "Introduce a CQRS pattern without breaking existing read path performance.",
        "Design a plugin system preserving 100% backward compat over 12 entry points.",
        "Implement a streaming parser for 10GB files with bounded memory <100MB.",
        "Rewrite a permission system with 4-role RBAC replacing ad-hoc checks.",
    ]
    for i, p in enumerate(easy_kinds):
        out.append(
            TaskSpec(
                task_id=f"swep-easy-{i:02d}",
                suite="swe-bench-pro",
                difficulty="easy",
                prompt=f"In repo {rng.choice(repos)}: {p}",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    for i, p in enumerate(med_kinds):
        out.append(
            TaskSpec(
                task_id=f"swep-med-{i:02d}",
                suite="swe-bench-pro",
                difficulty="medium",
                prompt=f"In repo {rng.choice(repos)}: {p}",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    for i, p in enumerate(hard_kinds):
        out.append(
            TaskSpec(
                task_id=f"swep-hard-{i:02d}",
                suite="swe-bench-pro",
                difficulty="hard",
                prompt=f"In repo {rng.choice(repos)}: {p}",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    for i, p in enumerate(ultra_kinds):
        out.append(
            TaskSpec(
                task_id=f"swep-ultra-{i:02d}",
                suite="swe-bench-pro",
                difficulty="ultra",
                prompt=f"In repo {rng.choice(repos)}: {p}",
                expected="passes_tests",
                reference="passes_tests",
                metadata={"repo": rng.choice(repos)},
            )
        )
    return out


def _bfcl_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    easy_kinds = [
        "Call get_weather(city='Tokyo'). Emit a single JSON tool_call.",
        "Call add(a=3, b=7). Emit a single JSON tool_call.",
        "Call list_files(dir='/tmp'). Emit a single JSON tool_call.",
        "Call search(query='python async'). Emit a single JSON tool_call.",
        "Call send_email(to='a@b.c', subject='hi'). Emit a single JSON tool_call.",
    ]
    med_kinds = [
        "Get the weather in Tokyo AND in Paris. Emit a single tool_calls array with both calls.",
        "Call add(a=3, b=7) and then multiply by 2. Emit a parallel tool_calls array.",
        "Resolve a chain: get_user(id=1) -> get_orders(user_id) -> get_total(order_id). Decide if all calls are needed.",
        "Read file A, then read file B (only if A doesn't exist). Emit conditional calls.",
        "Call send_email with retry: emit up to 3 calls if the first fails.",
        "Parse '3 + 7 * 2' and emit a calculator tool_call respecting precedence.",
        "Aggregate 3 parallel get_* calls and emit a final report without re-querying.",
        "Call get_weather and decide: if raining, also call notify_user().",
    ]
    hard_kinds = [
        "Tool chaining with state: call get_user, then call update_user with derived args.",
        "Multi-step reasoning: 3 sequential tool_calls where each result drives the next args.",
        "Parallel calls across heterogeneous tools (HTTP + DB + cache) for a single business task.",
        "Parse a natural-language request, decompose into 4 tool calls, emit all in one tool_calls array.",
        "Retry-with-fallback: try primary tool, on failure emit a backup tool call.",
        "Constraint-aware calling: call only tools whose preconditions are satisfied.",
        "Recursive resolution: call list_directory -> for each entry call get_metadata.",
    ]
    ultra_kinds = [
        "Orchestrate 5+ tools to complete a 7-step business workflow (book a meeting).",
        "Dynamic tool selection from 20+ available tools based on free-form NL.",
        "Cross-tool transaction: emit 4 calls that must all succeed or be rolled back.",
        "Adaptive retry: 3 retries with different tool variants on each failure.",
        "Multi-turn function calling with state preservation across 3 turns.",
    ]
    for i, p in enumerate(easy_kinds):
        out.append(
            TaskSpec(
                task_id=f"bfcl-easy-{i:02d}",
                suite="bfcl",
                difficulty="easy",
                prompt=p,
                expected="tool_call",
                reference="tool_call",
            )
        )
    for i, p in enumerate(med_kinds):
        out.append(
            TaskSpec(
                task_id=f"bfcl-med-{i:02d}",
                suite="bfcl",
                difficulty="medium",
                prompt=p,
                expected="tool_call",
                reference="tool_call",
            )
        )
    for i, p in enumerate(hard_kinds):
        out.append(
            TaskSpec(
                task_id=f"bfcl-hard-{i:02d}",
                suite="bfcl",
                difficulty="hard",
                prompt=p,
                expected="tool_call",
                reference="tool_call",
            )
        )
    for i, p in enumerate(ultra_kinds):
        out.append(
            TaskSpec(
                task_id=f"bfcl-ultra-{i:02d}",
                suite="bfcl",
                difficulty="ultra",
                prompt=p,
                expected="tool_call",
                reference="tool_call",
            )
        )
    return out


def _gpqa_diamond_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    domains = ["physics", "chemistry", "biology"]
    rng = random.Random("gpqa-diamond-2026")
    for i in range(DIFFICULTY_MIX["easy"]):
        out.append(
            TaskSpec(
                task_id=f"gpqa-easy-{i:02d}",
                suite="gpqa-diamond",
                difficulty="easy",
                prompt=f"[{rng.choice(domains)}] (graduate level, easy) Choose the correct answer from 4 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 4},
            )
        )
    for i in range(DIFFICULTY_MIX["medium"]):
        out.append(
            TaskSpec(
                task_id=f"gpqa-med-{i:02d}",
                suite="gpqa-diamond",
                difficulty="medium",
                prompt=f"[{rng.choice(domains)}] (graduate level, medium) Choose the correct answer from 4 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 4},
            )
        )
    for i in range(DIFFICULTY_MIX["hard"]):
        out.append(
            TaskSpec(
                task_id=f"gpqa-hard-{i:02d}",
                suite="gpqa-diamond",
                difficulty="hard",
                prompt=f"[{rng.choice(domains)}] (graduate level, hard) Choose the correct answer from 4 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 4},
            )
        )
    for i in range(DIFFICULTY_MIX["ultra"]):
        out.append(
            TaskSpec(
                task_id=f"gpqa-ultra-{i:02d}",
                suite="gpqa-diamond",
                difficulty="ultra",
                prompt=f"[{rng.choice(domains)}] (graduate level, ultra) Choose the correct answer from 4 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 4},
            )
        )
    return out


def _mmlu_pro_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    domains = [
        "philosophy",
        "economics",
        "law",
        "history",
        "math",
        "computer science",
        "engineering",
        "psychology",
    ]
    rng = random.Random("mmlu-pro-2026")
    for i in range(DIFFICULTY_MIX["easy"]):
        out.append(
            TaskSpec(
                task_id=f"mmlu-easy-{i:02d}",
                suite="mmlu-pro",
                difficulty="easy",
                prompt=f"[{rng.choice(domains)}] (college level, easy) Choose the correct answer from 10 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 10},
            )
        )
    for i in range(DIFFICULTY_MIX["medium"]):
        out.append(
            TaskSpec(
                task_id=f"mmlu-med-{i:02d}",
                suite="mmlu-pro",
                difficulty="medium",
                prompt=f"[{rng.choice(domains)}] (college level, medium) Choose the correct answer from 10 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 10},
            )
        )
    for i in range(DIFFICULTY_MIX["hard"]):
        out.append(
            TaskSpec(
                task_id=f"mmlu-hard-{i:02d}",
                suite="mmlu-pro",
                difficulty="hard",
                prompt=f"[{rng.choice(domains)}] (college level, hard) Choose the correct answer from 10 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 10},
            )
        )
    for i in range(DIFFICULTY_MIX["ultra"]):
        out.append(
            TaskSpec(
                task_id=f"mmlu-ultra-{i:02d}",
                suite="mmlu-pro",
                difficulty="ultra",
                prompt=f"[{rng.choice(domains)}] (college level, ultra) Choose the correct answer from 10 options.",
                expected="correct_letter",
                reference="correct_letter",
                metadata={"domain": rng.choice(domains), "options": 10},
            )
        )
    return out


def _terminal_bench_pool() -> list[TaskSpec]:
    out: list[TaskSpec] = []
    prompts_easy = [
        "echo the current date and time",
        "list all .py files in the current directory recursively",
        "print the value of the $PATH environment variable",
        "create a directory named 'pheno-test' and confirm with `ls`",
        "print the current working directory",
    ]
    prompts_med = [
        "find all files modified in the last 24 hours in /tmp and write to a list",
        "extract all unique email addresses from /etc/hosts* (none expected, just demonstrate parse)",
        "compress /tmp/codex-stock-vs-ours-probe into a tarball, then decompress and verify",
        "parse the JSON output of `date -u +%Y-%m-%dT%H:%M:%S` and echo the day-of-week",
        "set up a port forward from 127.0.0.1:9001 to 127.0.0.1:8765 using nc and verify",
        "tail -F /var/log/system.log for 5 seconds and count lines that contain 'error'",
        "use awk to print the sum of all numbers in column 3 of /tmp/some.csv (create it first if missing)",
        "find all files in /usr/local that are larger than 100MB and list them sorted by size",
    ]
    prompts_hard = [
        "parse a complex nested JSON config and extract 3 nested values into a flat dict",
        "use curl + jq to query a REST API and aggregate results across 5 paginated endpoints",
        "set up a 3-stage shell pipeline: extract -> transform -> load, and measure end-to-end wall time",
        "write a shell function that safely handles filenames with spaces and special characters",
        "implement exponential backoff retry logic in pure bash for an HTTP call",
        "parse /var/log/system.log (or create a mock), group errors by hour, print top 5",
        "implement a simple HTTP server in netcat that responds with JSON to GET /health",
    ]
    prompts_ultra = [
        "implement a minimal process supervisor in pure bash that auto-restarts on crash",
        "build a tiny distributed mutex across 3 shell processes using only /tmp/lockfile",
        "write a shell script that re-encodes a video using ffmpeg with progress reporting and ETA",
        "implement a 3-way merge of text files in pure bash (line-by-line, 3-way)",
        "build a self-recovering background daemon that restarts itself if killed",
    ]
    for i, p in enumerate(prompts_easy):
        out.append(
            TaskSpec(
                task_id=f"tb-easy-{i:02d}",
                suite="terminal-bench",
                difficulty="easy",
                prompt=p,
                expected="ok",
                reference="ok",
            )
        )
    for i, p in enumerate(prompts_med):
        out.append(
            TaskSpec(
                task_id=f"tb-med-{i:02d}",
                suite="terminal-bench",
                difficulty="medium",
                prompt=p,
                expected="ok",
                reference="ok",
            )
        )
    for i, p in enumerate(prompts_hard):
        out.append(
            TaskSpec(
                task_id=f"tb-hard-{i:02d}",
                suite="terminal-bench",
                difficulty="hard",
                prompt=p,
                expected="ok",
                reference="ok",
            )
        )
    for i, p in enumerate(prompts_ultra):
        out.append(
            TaskSpec(
                task_id=f"tb-ultra-{i:02d}",
                suite="terminal-bench",
                difficulty="ultra",
                prompt=p,
                expected="ok",
                reference="ok",
            )
        )
    return out
