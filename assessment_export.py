import json
from datetime import datetime


def build_assessment_summary(
    app_version,
    assessment_name,
    organization_name,
    prepared_by,
    total,
    ready,
    not_ready,
    readiness_score,
    readiness_grade,
    overall_risk_score,
    replacement_count,
    fixable_count,
    estimated_replacement_cost,
    category_counts,
    failure_counts,
    recommendations,
):
    """Build a portable assessment summary for history/trend analysis."""
    return {
        "app_version": app_version,
        "assessment_name": assessment_name,
        "organization_name": organization_name,
        "prepared_by": prepared_by,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_devices": int(total),
            "ready_devices": int(ready),
            "not_ready_devices": int(not_ready),
            "readiness_score": int(readiness_score),
            "readiness_grade": readiness_grade,
            "overall_risk_score": int(overall_risk_score),
            "replacement_required": int(replacement_count),
            "fixable": int(fixable_count),
            "estimated_replacement_cost": float(estimated_replacement_cost),
        },
        "category_counts": {
            str(category): int(count)
            for category, count in category_counts.items()
        },
        "failure_counts": {
            str(blocker): int(count)
            for blocker, count in failure_counts.items()
        },
        "recommendations": recommendations,
    }


def assessment_summary_to_json(summary):
    """Serialize the assessment summary as formatted JSON bytes."""
    return json.dumps(summary, indent=2).encode("utf-8")
