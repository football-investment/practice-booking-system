#!/usr/bin/env python3
"""Phase 6 monitoring: distractor pool health per question.

Usage:
  # Snapshot (default quiz)
  python scripts/monitoring/monitor_distractor_pool.py

  # Snapshot + save for later trend comparison
  python scripts/monitoring/monitor_distractor_pool.py --save-snapshot

  # Trend: compare current state to a saved snapshot
  python scripts/monitoring/monitor_distractor_pool.py \
      --compare-to scripts/monitoring/snapshots/2026-04-29_10-00.json

  # Log a content change after fixing a distractor
  python scripts/monitoring/monitor_distractor_pool.py --log-change \
      --q-id 2692 \
      --change "Weakened D4: removed 'ECA co-decision' framing → now 'ECA advisory only'" \
      --reason "SR 8% vs expected 28% — too strong"

  # All pool quizzes at once
  python scripts/monitoring/monitor_distractor_pool.py --all-pool-quizzes

What it measures:
  1. success_rate     — observed vs. seeded estimated_difficulty (inverse correlation expected)
  2. cross-question variance — flag questions that diverge from module average
  3. trend delta      — SR and attempt-count change vs. a saved snapshot

Thresholds:
  --sr-drop    Max tolerated SR drop from estimated baseline  (default 0.15)
  --sr-var     Max tolerated std deviation across questions   (default 0.18)

Decision rule (enforced in output, not in code):
  NEVER act on fewer than 10 attempts per question.
  Trend requires at least 24–48 h between snapshots.
  Change at most 1 distractor per question per intervention.

Exit codes:
  0 — all green
  1 — warnings present (review advised, do not act yet)
  2 — critical alerts (content action required if ≥10 attempts)
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database import SessionLocal
from app.models.quiz import Quiz, QuizQuestion, QuestionMetadata, UserQuestionPerformance

# ── Paths ─────────────────────────────────────────────────────────────────────

_MONITORING_DIR  = Path(__file__).resolve().parent
_SNAPSHOT_DIR    = _MONITORING_DIR / "snapshots"
_CHANGE_LOG_FILE = _MONITORING_DIR / "distractor_changes.jsonl"

# ── ANSI colours ──────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def _ok(msg):    return f"{GREEN}✓ {msg}{RESET}"
def _warn(msg):  return f"{YELLOW}⚠  {msg}{RESET}"
def _crit(msg):  return f"{RED}✗  {msg}{RESET}"
def _info(msg):  return f"   {msg}"
def _dim(msg):   return f"{DIM}{msg}{RESET}"
def _head(msg):  return f"\n{BOLD}{msg}{RESET}"


# ── Data layer ────────────────────────────────────────────────────────────────

def _pool_quizzes(db) -> list:
    from sqlalchemy import func
    from app.models.quiz import QuizAnswerOption
    rows = (
        db.query(Quiz)
        .join(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
        .join(QuizAnswerOption, QuizAnswerOption.question_id == QuizQuestion.id)
        .group_by(Quiz.id)
        .having(func.max(
            db.query(func.count(QuizAnswerOption.id))
            .filter(QuizAnswerOption.question_id == QuizQuestion.id)
            .correlate(QuizQuestion)
            .scalar_subquery()
        ) > 4)
        .all()
    )
    return rows


def _get_quiz(db, title: str):
    return db.query(Quiz).filter(Quiz.title == title).first()


def _question_stats(db, quiz) -> list[dict]:
    from sqlalchemy import func
    from app.models.quiz import QuizAnswerOption

    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz.id)
        .order_by(QuizQuestion.order_index)
        .all()
    )

    results = []
    for q in questions:
        meta = (
            db.query(QuestionMetadata)
            .filter(QuestionMetadata.question_id == q.id)
            .first()
        )
        perf_agg = (
            db.query(
                func.coalesce(func.sum(UserQuestionPerformance.total_attempts), 0),
                func.coalesce(func.sum(UserQuestionPerformance.correct_attempts), 0),
            )
            .filter(UserQuestionPerformance.question_id == q.id)
            .first()
        )

        total_att   = int(perf_agg[0]) if perf_agg[0] else 0
        correct_att = int(perf_agg[1]) if perf_agg[1] else 0
        obs_sr      = (correct_att / total_att) if total_att > 0 else None
        live_sr     = meta.global_success_rate if meta else None

        opt_count = (
            db.query(func.count(QuizAnswerOption.id))
            .filter(QuizAnswerOption.question_id == q.id)
            .scalar()
        )

        results.append({
            "id":                   q.id,
            "text":                 q.question_text[:65],
            "estimated_difficulty": meta.estimated_difficulty if meta else None,
            "seeded_time":          meta.average_time_seconds if meta else None,
            "live_sr":              live_sr,
            "obs_sr":               obs_sr if obs_sr is not None else live_sr,
            "total_attempts":       total_att,
            "correct_attempts":     correct_att,
            "opt_count":            opt_count,
        })

    return results


# ── Snapshot IO ───────────────────────────────────────────────────────────────

def _save_snapshot(quiz_title: str, stats: list[dict]) -> Path:
    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    path = _SNAPSHOT_DIR / f"{ts}.json"
    payload = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "quiz_title": quiz_title,
        "questions": [
            {
                "id":                   s["id"],
                "text":                 s["text"],
                "estimated_difficulty": s["estimated_difficulty"],
                "seeded_time":          s["seeded_time"],
                "obs_sr":               s["obs_sr"],
                "total_attempts":       s["total_attempts"],
                "correct_attempts":     s["correct_attempts"],
                "opt_count":            s["opt_count"],
            }
            for s in stats
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path


def _load_snapshot(path: str) -> dict:
    return json.loads(Path(path).read_text())


# ── Change log ────────────────────────────────────────────────────────────────

def _write_change_log(quiz_title: str, q_id: int, q_text: str,
                      change: str, reason: str) -> None:
    entry = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "quiz_title": quiz_title,
        "question_id":   q_id,
        "question_text": q_text,
        "change":     change,
        "reason":     reason,
    }
    with _CHANGE_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _print_change_log(last_n: int = 20) -> None:
    if not _CHANGE_LOG_FILE.exists():
        print(_info("No content changes logged yet."))
        return
    entries = [json.loads(l) for l in _CHANGE_LOG_FILE.read_text().splitlines() if l.strip()]
    if not entries:
        print(_info("Change log is empty."))
        return
    print(_head(f"CONTENT CHANGE LOG  (last {min(last_n, len(entries))} of {len(entries)})"))
    for e in entries[-last_n:]:
        ts_short = e["timestamp"][:16].replace("T", " ")
        print(f"\n   {BOLD}{ts_short}{RESET}  Q{e['question_id']}  {DIM}{e['question_text'][:55]}...{RESET}")
        print(f"   Change : {e['change']}")
        print(f"   Reason : {DIM}{e['reason']}{RESET}")


# ── Analysis ──────────────────────────────────────────────────────────────────

def _expected_sr(estimated_difficulty: float | None) -> float | None:
    if estimated_difficulty is None:
        return None
    return max(0.0, min(1.0, 1.0 - estimated_difficulty))


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _analyse(stats: list[dict], min_attempts: int, sr_drop: float,
             sr_var: float) -> tuple[list[str], list[str], list[str]]:
    ok, warn, crit = [], [], []

    observed_srs = [
        s["obs_sr"] for s in stats
        if s["obs_sr"] is not None and s["total_attempts"] >= min_attempts
    ]

    for s in stats:
        label = f'Q{s["id"]} "{s["text"]}..."'
        att   = s["total_attempts"]

        if att < min_attempts:
            ok.append(_dim(f'   {label}  →  {att} attempts  (need {min_attempts} before signal)'))
            continue

        sr     = s["obs_sr"]
        exp_sr = _expected_sr(s["estimated_difficulty"])

        if sr is not None and exp_sr is not None:
            drop = exp_sr - sr
            if drop > sr_drop:
                crit.append(_crit(
                    f'{label}\n'
                    f'     sr={sr:.2%}  expected≈{exp_sr:.2%}  drop={drop:.2%}'
                    f'  (threshold {sr_drop:.0%}) → distractors likely too strong'
                ))
            elif drop > sr_drop * 0.6:
                warn.append(_warn(
                    f'{label}\n'
                    f'     sr={sr:.2%}  expected≈{exp_sr:.2%}  drop={drop:.2%}'
                    f'  (approaching threshold — watch trend)'
                ))
            else:
                ok.append(_ok(f'{label}  sr={sr:.2%}  exp≈{exp_sr:.2%}  Δ={drop:+.2%}'))

    if len(observed_srs) >= 3:
        sigma   = _std(observed_srs)
        mean_sr = sum(observed_srs) / len(observed_srs)
        if sigma > sr_var:
            crit.append(_crit(
                f'Cross-question SR variance  σ={sigma:.3f} > {sr_var:.3f}'
                f'  mean={mean_sr:.2%} → distractor quality uneven across questions'
            ))
        elif sigma > sr_var * 0.7:
            warn.append(_warn(
                f'Cross-question SR variance σ={sigma:.3f}  mean={mean_sr:.2%}'
                f'  (approaching threshold)'
            ))
        else:
            ok.append(_ok(f'Cross-question SR variance  σ={sigma:.3f}  mean={mean_sr:.2%}'))
    else:
        ok.append(_dim(
            f'   Cross-question variance: {len(observed_srs)} questions with ≥{min_attempts} attempts'
            f' (need ≥3)'
        ))

    return ok, warn, crit


# ── Trend diff ────────────────────────────────────────────────────────────────

def _trend_section(current_stats: list[dict], snapshot: dict, min_attempts: int) -> list[str]:
    lines = []
    snap_ts   = snapshot.get("timestamp", "?")[:16].replace("T", " ")
    snap_map  = {q["id"]: q for q in snapshot.get("questions", [])}
    now_ts    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    lines.append(_head(f"TREND  ({snap_ts} UTC → {now_ts} UTC)"))

    any_signal = False
    for s in current_stats:
        prev = snap_map.get(s["id"])
        if not prev:
            continue

        att_delta = s["total_attempts"] - prev["total_attempts"]
        if att_delta < 1:
            lines.append(_dim(f'   Q{s["id"]}  no new attempts since snapshot'))
            continue

        any_signal = True
        curr_sr = s["obs_sr"]
        prev_sr = prev.get("obs_sr")
        exp_sr  = _expected_sr(s["estimated_difficulty"])

        sr_delta_str = "—"
        sr_flag      = ""
        if curr_sr is not None and prev_sr is not None:
            delta = curr_sr - prev_sr
            sign  = "+" if delta >= 0 else ""
            sr_delta_str = f"{sign}{delta:.2%}"
            if delta < -0.08:
                sr_flag = f"  {YELLOW}↓ declining{RESET}"
            elif delta > 0.08:
                sr_flag = f"  {GREEN}↑ improving{RESET}"

        curr_sr_str = f"{curr_sr:.2%}" if curr_sr is not None else "—"
        prev_sr_str = f"{prev_sr:.2%}" if prev_sr is not None else "—"
        exp_str     = f"{exp_sr:.2%}" if exp_sr is not None else "—"

        # Decision gate
        if s["total_attempts"] < min_attempts:
            gate = _dim(f"  ⚑ {s['total_attempts']} attempts — below {min_attempts} threshold, no action")
        else:
            gate = ""

        lines.append(
            f"   Q{s['id']}  att +{att_delta:>3}  sr {prev_sr_str} → {curr_sr_str}"
            f"  Δ={sr_delta_str}  exp≈{exp_str}{sr_flag}{gate}"
        )

    if not any_signal:
        lines.append(_dim("   No new attempts recorded since snapshot."))

    return lines


# ── Report ────────────────────────────────────────────────────────────────────

def _print_report(quiz, stats: list[dict], ok: list, warn: list, crit: list,
                  min_attempts: int, trend_lines: list[str]) -> int:
    total_att = sum(s["total_attempts"] for s in stats)
    pool_qs   = sum(1 for s in stats if s["opt_count"] > 4)

    print(_head(f"DISTRACTOR POOL HEALTH — {quiz.title}"))
    print(f"   Questions: {len(stats)}  |  Pool questions: {pool_qs}  |  Total attempts: {total_att}")
    print(f"   {DIM}Action gate: ≥{min_attempts} attempts required before any content change{RESET}\n")

    # Stats table
    print(f"   {'Q-ID':<6} {'Opts':<5} {'Attempts':<10} {'Obs SR':<10} {'Exp SR':<10} {'Δ-SR':<10}")
    print(f"   {'─'*55}")
    for s in stats:
        sr_str  = f"{s['obs_sr']:.2%}"  if s["obs_sr"] is not None  else "—"
        exp_str = f"{_expected_sr(s['estimated_difficulty']):.2%}" if s["estimated_difficulty"] else "—"
        if s["obs_sr"] is not None and _expected_sr(s["estimated_difficulty"]) is not None:
            delta = _expected_sr(s["estimated_difficulty"]) - s["obs_sr"]
            d_str = f"{delta:+.2%}"
            flag  = f"  {RED}◀{RESET}" if delta > 0.15 else (f"  {YELLOW}▲{RESET}" if delta > 0.09 else "")
        else:
            d_str, flag = "—", ""
        print(f"   {s['id']:<6} {s['opt_count']:<5} {s['total_attempts']:<10} {sr_str:<10} {exp_str:<10} {d_str}{flag}")

    # Trend section
    for line in trend_lines:
        print(line)

    if crit:
        print(_head("CRITICAL"))
        for line in crit:
            print(line)

    if warn:
        print(_head("WARNINGS"))
        for line in warn:
            print(line)

    if ok:
        print(_head("OK"))
        for line in ok:
            print(line)

    if crit or warn:
        print(_head("CORRECTION GUIDE  (content only — no code, no schema changes)"))
        if crit:
            print(f"  {BOLD}SR drop > threshold:{RESET}")
            print("    1. Identify the strongest distractor in the question (most plausible wrong answer)")
            print("    2. Weaken it by making one detail more obviously incorrect")
            print("    3. Change at most 1 distractor per question per intervention")
            print("    4. Log the change:  --log-change --q-id <id> --change '...' --reason '...'")
            print("    5. DELETE quiz + reseed, then re-run this script after ≥10 new attempts")
        if warn:
            print(f"  {BOLD}Variance / approaching threshold:{RESET}")
            print("    → Do not act until ≥10 attempts AND trend confirms sustained direction")
            print("    → One kilengés ≠ trigger")

    if crit:
        print(f"\n{RED}{BOLD}Status: CRITICAL{RESET}  (act only if ≥{min_attempts} attempts confirmed)")
        return 2
    if warn:
        print(f"\n{YELLOW}{BOLD}Status: WARNINGS{RESET}  (watch trend — no action yet)")
        return 1
    print(f"\n{GREEN}{BOLD}Status: ALL GREEN{RESET}")
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Distractor pool health monitor — Phase 6",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # --- mode flags ---
    parser.add_argument(
        "--quiz",
        default="AL — Football Awareness - Football Governance & Global Structures [EN]",
        help="Exact quiz title to inspect",
    )
    parser.add_argument(
        "--all-pool-quizzes", action="store_true",
        help="Report for all quizzes with pool questions (>4 options)",
    )
    parser.add_argument(
        "--save-snapshot", action="store_true",
        help="Save current stats as a timestamped snapshot for later trend comparison",
    )
    parser.add_argument(
        "--compare-to", metavar="SNAPSHOT_FILE",
        help="Compare current stats to a saved snapshot (trend report)",
    )

    # --- change log ---
    parser.add_argument(
        "--log-change", action="store_true",
        help="Log a content change to distractor_changes.jsonl",
    )
    parser.add_argument("--q-id",   type=int,  help="Question ID for --log-change")
    parser.add_argument("--change", type=str,  help="Description of the distractor change")
    parser.add_argument("--reason", type=str,  help="Reason / metric that triggered the change")
    parser.add_argument(
        "--show-log", action="store_true",
        help="Print the content change log and exit",
    )

    # --- thresholds ---
    parser.add_argument(
        "--min-attempts", type=int, default=10,
        help="Minimum attempts before signal is reportable (default: 10)",
    )
    parser.add_argument(
        "--sr-drop", type=float, default=0.15,
        help="Max tolerated SR drop from estimated baseline (default: 0.15)",
    )
    parser.add_argument(
        "--sr-var", type=float, default=0.18,
        help="Max tolerated cross-question SR std deviation (default: 0.18)",
    )

    args = parser.parse_args()

    # ── Show change log mode ────────────────────────────────────────────────
    if args.show_log:
        _print_change_log()
        return 0

    # ── Log-change mode ─────────────────────────────────────────────────────
    if args.log_change:
        if not all([args.q_id, args.change, args.reason]):
            print("--log-change requires --q-id, --change, and --reason")
            return 1
        db = SessionLocal()
        try:
            q = db.query(QuizQuestion).filter(QuizQuestion.id == args.q_id).first()
            q_text = q.question_text[:65] if q else f"(Q{args.q_id} not found)"
            quiz_q = db.query(Quiz).filter(Quiz.id == q.quiz_id).first() if q else None
            quiz_title = quiz_q.title if quiz_q else args.quiz
        finally:
            db.close()
        _write_change_log(quiz_title, args.q_id, q_text, args.change, args.reason)
        print(_ok(f"Change logged → {_CHANGE_LOG_FILE}"))
        print(f"   Q{args.q_id}: {q_text}...")
        print(f"   Change : {args.change}")
        print(f"   Reason : {args.reason}")
        return 0

    # ── Normal monitoring mode ───────────────────────────────────────────────
    db = SessionLocal()
    exit_code = 0
    snapshot  = _load_snapshot(args.compare_to) if args.compare_to else None

    try:
        if args.all_pool_quizzes:
            quizzes = _pool_quizzes(db)
            if not quizzes:
                print("No pool quizzes found.")
                return 0
        else:
            quiz = _get_quiz(db, args.quiz)
            if not quiz:
                print(f"Quiz not found: {args.quiz!r}")
                return 1
            quizzes = [quiz]

        for quiz in quizzes:
            stats       = _question_stats(db, quiz)
            ok, warn, crit = _analyse(stats, args.min_attempts, args.sr_drop, args.sr_var)
            trend_lines = _trend_section(stats, snapshot, args.min_attempts) if snapshot else []

            code = _print_report(quiz, stats, ok, warn, crit, args.min_attempts, trend_lines)
            exit_code = max(exit_code, code)

            if args.save_snapshot:
                path = _save_snapshot(quiz.title, stats)
                print(f"\n{GREEN}Snapshot saved → {path}{RESET}")

    finally:
        db.close()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
