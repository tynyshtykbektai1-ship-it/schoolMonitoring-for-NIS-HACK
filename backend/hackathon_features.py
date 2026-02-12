from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse


SEVERITY_WEIGHTS = {
    "tab_switch": 2.0,
    "face_not_found": 2.5,
    "multiple_faces": 4.0,
    "phone_detected": 5.0,
    "suspicious_window": 3.0,
}


def _parse_timestamp(raw_value: str | None) -> datetime:
    if not raw_value:
        return datetime.now()

    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
        try:
            return datetime.strptime(raw_value, fmt)
        except ValueError:
            continue

    return datetime.now()


def _risk_level(score: float) -> str:
    if score >= 30:
        return "critical"
    if score >= 15:
        return "high"
    if score >= 7:
        return "medium"
    return "low"


def _compute_student_risks(violations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now()
    by_student: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"incidents": 0, "risk_score": 0.0, "last_incident_at": None, "types": Counter()}
    )

    for violation in violations:
        student_id = violation.get("student_id", "unknown")
        violation_type = violation.get("violation_type", "unknown")
        ts = _parse_timestamp(violation.get("timestamp"))

        age_minutes = max((now - ts).total_seconds() / 60, 0.0)
        recency_factor = 1.0 / (1.0 + (age_minutes / 20.0))
        base_weight = SEVERITY_WEIGHTS.get(violation_type, 1.5)

        entry = by_student[student_id]
        entry["incidents"] += 1
        entry["risk_score"] += base_weight * recency_factor
        entry["types"][violation_type] += 1

        if entry["last_incident_at"] is None or ts > entry["last_incident_at"]:
            entry["last_incident_at"] = ts

    result: List[Dict[str, Any]] = []
    for student_id, data in by_student.items():
        score = round(data["risk_score"], 2)
        result.append(
            {
                "student_id": student_id,
                "incidents": data["incidents"],
                "risk_score": score,
                "risk_level": _risk_level(score),
                "last_incident_at": data["last_incident_at"].isoformat() if data["last_incident_at"] else None,
                "top_violation_type": data["types"].most_common(1)[0][0] if data["types"] else "unknown",
            }
        )

    result.sort(key=lambda x: (x["risk_score"], x["incidents"]), reverse=True)
    return result


def create_hackathon_router(
    get_violations: Callable[[], List[Dict[str, Any]]],
    get_active_students: Callable[[], Dict[str, Any]],
    get_last_frames: Callable[[], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/api/hackathon", tags=["hackathon"])

    @router.get("/overview")
    async def overview():
        violations = get_violations()
        active_students = get_active_students()
        last_frames = get_last_frames()
        risk_table = _compute_student_risks(violations)

        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        active_alerts = 0
        for v in violations:
            if _parse_timestamp(v.get("timestamp")) >= ten_minutes_ago:
                active_alerts += 1

        type_counter = Counter(v.get("violation_type", "unknown") for v in violations)

        return JSONResponse(
            {
                "total_students_online": len(active_students),
                "students_with_live_frames": len(last_frames),
                "total_violations": len(violations),
                "active_alerts_last_10m": active_alerts,
                "top_risky_students": risk_table[:5],
                "violation_type_breakdown": dict(type_counter),
            }
        )

    @router.get("/leaderboard")
    async def leaderboard(limit: int = Query(10, ge=1, le=100)):
        violations = get_violations()
        risks = _compute_student_risks(violations)
        return JSONResponse({"leaderboard": risks[:limit]})

    @router.get("/timeline")
    async def timeline(minutes: int = Query(120, ge=10, le=24 * 60)):
        violations = get_violations()
        from_ts = datetime.now() - timedelta(minutes=minutes)
        buckets: Dict[str, int] = defaultdict(int)

        for violation in violations:
            ts = _parse_timestamp(violation.get("timestamp"))
            if ts < from_ts:
                continue
            key = ts.strftime("%Y-%m-%d %H:%M")
            buckets[key] += 1

        ordered = sorted(buckets.items(), key=lambda item: item[0])
        peak = max(ordered, key=lambda item: item[1], default=(None, 0))

        return JSONResponse(
            {
                "window_minutes": minutes,
                "points": [{"minute": minute, "incidents": count} for minute, count in ordered],
                "peak_minute": {"minute": peak[0], "incidents": peak[1]} if peak[0] else None,
            }
        )

    @router.get("/student/{student_id}/insights")
    async def student_insights(student_id: str):
        violations = [v for v in get_violations() if v.get("student_id") == student_id]
        risks = _compute_student_risks(violations)
        student_risk = risks[0] if risks else None

        if not violations:
            return JSONResponse(
                {
                    "student_id": student_id,
                    "incidents": 0,
                    "status": "clean",
                    "insight": "No violations recorded yet.",
                    "recommendation": "Keep monitoring in passive mode.",
                }
            )

        type_counter = Counter(v.get("violation_type", "unknown") for v in violations)
        top_type, top_count = type_counter.most_common(1)[0]

        recommendation = {
            "tab_switch": "Ask student to keep only one test window open.",
            "face_not_found": "Request camera angle adjustment.",
            "multiple_faces": "Require immediate room re-check.",
            "phone_detected": "Do a manual integrity check now.",
        }.get(top_type, "Run a short manual check with the student.")

        return JSONResponse(
            {
                "student_id": student_id,
                "incidents": len(violations),
                "risk": student_risk or {},
                "dominant_violation_type": top_type,
                "dominant_violation_count": top_count,
                "insight": f"Most repeated issue is '{top_type}'.",
                "recommendation": recommendation,
            }
        )

    return router
