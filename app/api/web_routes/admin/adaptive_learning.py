"""Admin Adaptive Learning — read-only knowledge base browser + JSON import center."""
import json
import logging
import math

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ....database import get_db
from ....dependencies import get_current_user_web
from ....models.al_import_log import ALImportLog, ImportStatus
from ....models.quiz import Quiz, QuizQuestion, QuizAnswerOption, OptionType
from ....models.user import User
from ....services.al_import_service import (
    SPECIALIZATION_CATEGORY_ALLOWLIST,
    _MAX_FILES_PER_IMPORT,
    validate_files,
    apply_import,
)
from . import _admin_guard, templates

logger = logging.getLogger(__name__)

router = APIRouter()

_KNOWN_SPECS = list(SPECIALIZATION_CATEGORY_ALLOWLIST.keys())
_DEFAULT_SPEC = "LFA_FOOTBALL_PLAYER"
_QUIZZES_PER_PAGE = 30
_HISTORY_PER_PAGE = 20


# ── AL-01  Dashboard ──────────────────────────────────────────────────────────

@router.get("/admin/adaptive-learning/dashboard", response_class=HTMLResponse)
async def al_dashboard(
    request: Request,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user_web),
):
    _admin_guard(user)

    total_quizzes    = db.query(Quiz).count()
    active_quizzes   = db.query(Quiz).filter(Quiz.is_active == True).count()
    total_questions  = db.query(QuizQuestion).count()
    total_options    = db.query(QuizAnswerOption).count()
    variant_options  = db.query(QuizAnswerOption).filter(
        QuizAnswerOption.option_type == OptionType.CORRECT_VARIANT
    ).count()
    distractor_options = db.query(QuizAnswerOption).filter(
        QuizAnswerOption.option_type == OptionType.DISTRACTOR
    ).count()
    recent_imports = (
        db.query(ALImportLog)
        .order_by(ALImportLog.completed_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse("admin/al_dashboard.html", {
        "request":             request,
        "total_quizzes":       total_quizzes,
        "active_quizzes":      active_quizzes,
        "total_questions":     total_questions,
        "total_options":       total_options,
        "variant_options":     variant_options,
        "distractor_options":  distractor_options,
        "recent_imports":      recent_imports,
        "ImportStatus":        ImportStatus,
    })


# ── AL-02  Quiz list ──────────────────────────────────────────────────────────

@router.get("/admin/adaptive-learning/quizzes", response_class=HTMLResponse)
async def al_quiz_list(
    request: Request,
    page: int = 1,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user_web),
):
    _admin_guard(user)

    total  = db.query(Quiz).count()
    offset = (page - 1) * _QUIZZES_PER_PAGE
    quizzes = (
        db.query(Quiz)
        .order_by(Quiz.id.asc())
        .offset(offset)
        .limit(_QUIZZES_PER_PAGE)
        .all()
    )
    total_pages = math.ceil(total / _QUIZZES_PER_PAGE) if total else 1

    return templates.TemplateResponse("admin/al_quiz_list.html", {
        "request":     request,
        "quizzes":     quizzes,
        "page":        page,
        "total_pages": total_pages,
        "total":       total,
    })


# ── AL-03  Quiz detail (with question list) ───────────────────────────────────

@router.get("/admin/adaptive-learning/quizzes/{quiz_id}", response_class=HTMLResponse)
async def al_quiz_detail(
    quiz_id: int,
    request: Request,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user_web),
):
    _admin_guard(user)

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        return RedirectResponse(
            "/admin/adaptive-learning/quizzes?error=Quiz+not+found",
            status_code=303,
        )

    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.order_index.asc())
        .all()
    )

    return templates.TemplateResponse("admin/al_quiz_detail.html", {
        "request":   request,
        "quiz":      quiz,
        "questions": questions,
    })


# ── AL-04  Question detail (read-only) ────────────────────────────────────────

@router.get(
    "/admin/adaptive-learning/quizzes/{quiz_id}/questions/{question_id}",
    response_class=HTMLResponse,
)
async def al_question_detail(
    quiz_id:     int,
    question_id: int,
    request: Request,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user_web),
):
    _admin_guard(user)

    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    question = db.query(QuizQuestion).filter(
        QuizQuestion.id == question_id,
        QuizQuestion.quiz_id == quiz_id,
    ).first()

    if not quiz or not question:
        return RedirectResponse(
            f"/admin/adaptive-learning/quizzes/{quiz_id}?error=Question+not+found",
            status_code=303,
        )

    options = (
        db.query(QuizAnswerOption)
        .filter(QuizAnswerOption.question_id == question_id)
        .order_by(QuizAnswerOption.order_index.asc())
        .all()
    )

    return templates.TemplateResponse("admin/al_question_detail.html", {
        "request":  request,
        "quiz":     quiz,
        "question": question,
        "options":  options,
        "OptionType": OptionType,
    })


# ── AL-05  Import form ────────────────────────────────────────────────────────

@router.get("/admin/adaptive-learning/import", response_class=HTMLResponse)
async def al_import_form(
    request: Request,
    user: User = Depends(get_current_user_web),
):
    _admin_guard(user)

    return templates.TemplateResponse("admin/al_import.html", {
        "request":           request,
        "known_specs":       _KNOWN_SPECS,
        "default_spec":      _DEFAULT_SPEC,
        "max_files":         _MAX_FILES_PER_IMPORT,
        "report":            None,
        "apply_payload_json": "",
        "error":             request.query_params.get("error", ""),
        "success":           request.query_params.get("success", ""),
    })


# ── AL-06  Import validate (dry-run, re-renders form with report) ─────────────

@router.post("/admin/adaptive-learning/import/validate", response_class=HTMLResponse)
async def al_import_validate(
    request: Request,
    spec:    str            = Form(_DEFAULT_SPEC),
    files:   list[UploadFile] = File(...),
    db:      Session        = Depends(get_db),
    user:    User           = Depends(get_current_user_web),
):
    _admin_guard(user)

    if spec not in _KNOWN_SPECS:
        return RedirectResponse(
            f"/admin/adaptive-learning/import?error=Unknown+spec+{spec}",
            status_code=303,
        )

    if len(files) > _MAX_FILES_PER_IMPORT:
        return RedirectResponse(
            f"/admin/adaptive-learning/import?error=Too+many+files+%28max+{_MAX_FILES_PER_IMPORT}%29",
            status_code=303,
        )

    raw_files: list[tuple[str, bytes]] = []
    for upload in files:
        content = await upload.read()
        raw_files.append((upload.filename or "unnamed.json", content))

    try:
        report = validate_files(raw_files, spec, db)
    except ValueError as exc:
        return RedirectResponse(
            f"/admin/adaptive-learning/import?error={str(exc)[:200]}",
            status_code=303,
        )

    return templates.TemplateResponse("admin/al_import.html", {
        "request":            request,
        "known_specs":        _KNOWN_SPECS,
        "default_spec":       spec,
        "max_files":          _MAX_FILES_PER_IMPORT,
        "report":             report,
        "apply_payload_json": report.apply_payload_json,
        "error":              "",
        "success":            "",
    })


# ── AL-07  Import apply ───────────────────────────────────────────────────────

@router.post("/admin/adaptive-learning/import/apply", response_class=HTMLResponse)
async def al_import_apply(
    request: Request,
    spec:                str  = Form(_DEFAULT_SPEC),
    apply_payload_json:  str  = Form(""),
    db:   Session             = Depends(get_db),
    user: User                = Depends(get_current_user_web),
):
    _admin_guard(user)

    if not apply_payload_json:
        return RedirectResponse(
            "/admin/adaptive-learning/import?error=No+validated+payload.+Upload+files+first.",
            status_code=303,
        )
    if spec not in _KNOWN_SPECS:
        return RedirectResponse(
            f"/admin/adaptive-learning/import?error=Unknown+spec+{spec}",
            status_code=303,
        )

    try:
        summary = apply_import(
            apply_payload_json=apply_payload_json,
            spec=spec,
            db=db,
            operator_user_id=user.id,
        )
    except ValueError as exc:
        return RedirectResponse(
            f"/admin/adaptive-learning/import?error={str(exc)[:200]}",
            status_code=303,
        )
    except Exception as exc:
        logger.exception("AL import apply failed")
        return RedirectResponse(
            f"/admin/adaptive-learning/import?error=Import+failed%3A+{str(exc)[:150]}",
            status_code=303,
        )

    return templates.TemplateResponse("admin/al_import_success.html", {
        "request": request,
        "summary": summary,
        "spec":    spec,
        "log_id":  summary.log_id,
    })


# ── AL-08  Import history ─────────────────────────────────────────────────────

@router.get("/admin/adaptive-learning/import/history", response_class=HTMLResponse)
async def al_import_history(
    request: Request,
    page: int = 1,
    db:   Session = Depends(get_db),
    user: User    = Depends(get_current_user_web),
):
    _admin_guard(user)

    total  = db.query(ALImportLog).count()
    offset = (page - 1) * _HISTORY_PER_PAGE
    logs   = (
        db.query(ALImportLog)
        .order_by(ALImportLog.completed_at.desc())
        .offset(offset)
        .limit(_HISTORY_PER_PAGE)
        .all()
    )
    total_pages = math.ceil(total / _HISTORY_PER_PAGE) if total else 1

    return templates.TemplateResponse("admin/al_import_history.html", {
        "request":     request,
        "logs":        logs,
        "page":        page,
        "total_pages": total_pages,
        "total":       total,
        "ImportStatus": ImportStatus,
    })
