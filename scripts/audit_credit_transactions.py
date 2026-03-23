"""
audit_credit_transactions.py — Static AST audit for credit_balance mutations.

Scans app/ for functions that mutate .credit_balance (augmented or plain
assignment) without a matching CreditTransaction instantiation in the same
function scope.  Such gaps mean balance changes happen without an audit trail.

Usage:
    python scripts/audit_credit_transactions.py             # report only
    python scripts/audit_credit_transactions.py --exit-code # exit 1 on violations
    python scripts/audit_credit_transactions.py --root app/api
"""

import ast
import argparse
import sys
from pathlib import Path


# ── AST helpers ───────────────────────────────────────────────────────────────

def _shallow_walk(node: ast.AST):
    """
    Yield all AST nodes in a subtree WITHOUT descending into nested
    function / class definitions.

    Nested FunctionDef / AsyncFunctionDef / ClassDef nodes are yielded
    (so their start line is available) but their children are NOT traversed —
    they will be visited separately by the outer ast.walk() loop.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield child          # surface boundary node, stop recursion
        else:
            yield from _shallow_walk(child)


def _is_credit_balance_assignment(node: ast.AST) -> bool:
    """True if node is an augmented or plain assignment to *.credit_balance."""
    if isinstance(node, ast.AugAssign):
        t = node.target
        return isinstance(t, ast.Attribute) and t.attr == "credit_balance"
    if isinstance(node, ast.Assign):
        return any(
            isinstance(t, ast.Attribute) and t.attr == "credit_balance"
            for t in node.targets
        )
    return False


def _mutation_lines(func_node: ast.AST) -> list[int]:
    """Line numbers of credit_balance mutations directly inside func_node."""
    lines = []
    for node in _shallow_walk(func_node):
        if node is func_node:
            continue                          # skip the FunctionDef wrapper itself
        if _is_credit_balance_assignment(node):
            lines.append(node.lineno)
    return lines


def _has_credit_transaction(func_node: ast.AST) -> bool:
    """
    True if func_node's direct scope contains a credit audit call.

    Accepted patterns:
      CreditTransaction(...)                  — direct instantiation
      models.CreditTransaction(...)           — qualified instantiation
      credit_service.create_transaction(...)  — service-layer wrapper
      <any>.create_transaction(...)           — any other service wrapper
    """
    for node in _shallow_walk(func_node):
        if node is func_node:
            continue
        if isinstance(node, ast.Call):
            func = node.func
            # Direct: CreditTransaction(...)
            if isinstance(func, ast.Name) and func.id == "CreditTransaction":
                return True
            if isinstance(func, ast.Attribute):
                # Qualified: foo.CreditTransaction(...)
                if func.attr == "CreditTransaction":
                    return True
                # Service wrapper: foo.create_transaction(...)
                if func.attr == "create_transaction":
                    return True
    return False


# ── File auditor ──────────────────────────────────────────────────────────────

def audit_file(path: Path) -> list[dict]:
    """Return a list of violation dicts found in a single Python file."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        lines = _mutation_lines(node)
        if not lines:
            continue

        if not _has_credit_transaction(node):
            violations.append(
                {
                    "file": str(path),
                    "function": node.name,
                    "func_line": node.lineno,
                    "mutation_lines": lines,
                }
            )

    return violations


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit credit_balance mutations for missing CreditTransaction logging."
    )
    parser.add_argument(
        "--root",
        default="app",
        help="Root directory to scan (default: app)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=["app/tests"],
        metavar="DIR",
        help="Subdirectory path to exclude (default: app/tests). Repeatable.",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with non-zero status if violations are found",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: directory not found: {root}", file=sys.stderr)
        return 2

    exclude_roots = [Path(e) for e in args.exclude]

    def _is_excluded(path: Path) -> bool:
        for ex in exclude_roots:
            try:
                path.relative_to(ex)
                return True
            except ValueError:
                pass
        return False

    all_violations: list[dict] = []
    for py_file in sorted(root.rglob("*.py")):
        if _is_excluded(py_file):
            continue
        all_violations.extend(audit_file(py_file))

    sep = "=" * 70

    if all_violations:
        print(f"\n{sep}")
        print(f"CREDIT BALANCE AUDIT — {len(all_violations)} VIOLATION(S)")
        print(sep)
        for v in all_violations:
            print(f"\n  FILE     : {v['file']}")
            print(f"  FUNCTION : {v['function']}  (defined at line {v['func_line']})")
            print(f"  MUTATIONS: credit_balance assigned at lines {v['mutation_lines']}")
            print(
                "  REQUIRED : a CreditTransaction(...) must be created in the same function"
            )
        print(f"\n{sep}")
        print(
            f"❌  {len(all_violations)} violation(s) found — "
            "credit_balance mutated without audit log"
        )
        print("    Each mutation needs a matching CreditTransaction entry.")
        print("    Reference: app/models/credit_transaction.py")
        return 1 if args.exit_code else 0

    print(f"\n{sep}")
    print("CREDIT BALANCE AUDIT — CLEAN")
    print(sep)
    print("✅  All credit_balance mutations have a CreditTransaction log entry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
