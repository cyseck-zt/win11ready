def build_rule_based_recommendations(
    readiness_score,
    overall_risk_score,
    replacement_count,
    fixable_count,
    failure_counts,
):
    """Generate non-AI executive recommendations from assessment results."""
    recommendations = []

    if readiness_score >= 90:
        recommendations.append(
            "Begin phased Windows 11 deployment with devices marked as Ready. Maintain a remediation backlog for the remaining blocked devices."
        )
    elif readiness_score >= 70:
        recommendations.append(
            "Start remediation planning before broad deployment. A pilot deployment can begin with Ready devices while blocked systems are addressed."
        )
    else:
        recommendations.append(
            "Delay broad Windows 11 deployment until major blockers are remediated. Current readiness is too low for a low-risk rollout."
        )

    if fixable_count > 0:
        recommendations.append(
            f"Prioritize the {fixable_count} fixable device(s). These systems may be recoverable through BIOS, firmware, Secure Boot, TPM, or storage remediation."
        )

    if replacement_count > 0:
        recommendations.append(
            f"Create a hardware refresh plan for the {replacement_count} device(s) categorized as Replacement Required. These devices are unlikely to be practical Windows 11 candidates."
        )

    if not failure_counts.empty:
        top_blocker = failure_counts.index[0]
        top_count = int(failure_counts.iloc[0])
        recommendations.append(
            f"Focus first on the top blocker: {top_blocker}. It affects {top_count} device(s) and represents the largest readiness improvement opportunity."
        )

    if overall_risk_score >= 70:
        recommendations.append(
            "Overall risk is high. Leadership should expect remediation effort, hardware replacement costs, and possible deployment delays."
        )
    elif overall_risk_score >= 40:
        recommendations.append(
            "Overall risk is moderate. Continue with controlled deployment planning while IT remediates known blockers."
        )
    else:
        recommendations.append(
            "Overall risk is low. The environment appears suitable for a staged Windows 11 rollout."
        )

    return recommendations


def build_readiness_interpretation(readiness_score, readiness_grade):
    """Return a short plain-English interpretation of the readiness grade."""
    if readiness_grade == "A":
        return "Excellent readiness. The environment appears highly prepared for Windows 11 deployment."
    if readiness_grade == "B":
        return "Strong readiness. Most devices are prepared, with a manageable remediation backlog."
    if readiness_grade == "C":
        return "Moderate readiness. Deployment is possible, but remediation should be completed first for blocked systems."
    if readiness_grade == "D":
        return "Low readiness. Significant blockers remain and deployment planning should be cautious."
    return "Poor readiness. The environment requires substantial remediation or hardware refresh before deployment."
