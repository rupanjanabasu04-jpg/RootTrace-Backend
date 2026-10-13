from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.dependency import ServiceDependency
from app.models.deployment import Deployment
from app.models.event import Event
from app.models.evidence import Evidence
from app.models.hypothesis import Hypothesis
from app.models.service import Service


def analyze_incident(
    incident_id: UUID,
    db: Session,
) -> dict:
    """
    Build a deterministic incident analysis from stored facts.

    The analyzer does not use AI.
    It only uses database facts, timing, dependencies,
    hypotheses, and evidence.
    """

    # ---------------------------------------------------------
    # 1. Load incident facts
    # ---------------------------------------------------------

    events = (
        db.query(Event)
        .filter(Event.incident_id == incident_id)
        .order_by(Event.occurred_at.asc())
        .all()
    )

    deployments = (
        db.query(Deployment)
        .filter(Deployment.incident_id == incident_id)
        .order_by(Deployment.occurred_at.asc())
        .all()
    )

    hypotheses = (
        db.query(Hypothesis)
        .filter(Hypothesis.incident_id == incident_id)
        .order_by(Hypothesis.score.desc())
        .all()
    )

    # ---------------------------------------------------------
    # 2. Load services and dependencies
    # ---------------------------------------------------------

    services = db.query(Service).all()

    service_map = {
        service.id: service.name
        for service in services
    }

    dependencies = db.query(ServiceDependency).all()

    # ---------------------------------------------------------
    # 3. Build timeline
    # ---------------------------------------------------------

    timeline = []

    for deployment in deployments:
        timeline.append(
            {
                "timestamp": deployment.occurred_at,
                "type": "deployment",
                "service": service_map.get(
                    deployment.service_id,
                    "Unknown",
                ),
                "message": deployment.description
                or f"Deployment {deployment.version or ''}".strip(),
                "source_id": str(deployment.id),
            }
        )

    for event in events:
        timeline.append(
            {
                "timestamp": event.occurred_at,
                "type": event.event_type,
                "service": service_map.get(
                    event.service_id,
                    "Unknown",
                ),
                "message": event.message,
                "source_id": str(event.id),
            }
        )

    timeline.sort(key=lambda item: item["timestamp"])

    # Convert datetime values to strings for JSON response.
    timeline_response = [
        {
            **item,
            "timestamp": item["timestamp"].isoformat(),
        }
        for item in timeline
    ]

    # ---------------------------------------------------------
    # 4. Find temporal correlations
    # ---------------------------------------------------------

    temporal_correlations = []

    for deployment in deployments:
        for event in events:
            if event.occurred_at >= deployment.occurred_at:
                difference_seconds = (
                    event.occurred_at - deployment.occurred_at
                ).total_seconds()

                difference_minutes = difference_seconds / 60

                # Consider changes within 30 minutes temporally relevant.
                if difference_minutes <= 30:
                    temporal_correlations.append(
                        {
                            "deployment_id": str(deployment.id),
                            "event_id": str(event.id),
                            "deployment_service": service_map.get(
                                deployment.service_id,
                                "Unknown",
                            ),
                            "event_service": service_map.get(
                                event.service_id,
                                "Unknown",
                            ),
                            "delay_minutes": round(
                                difference_minutes,
                                2,
                            ),
                            "reason": (
                                f"The event occurred "
                                f"{round(difference_minutes, 2)} "
                                f"minutes after the deployment."
                            ),
                        }
                    )

    # ---------------------------------------------------------
    # 5. Build dependency relationships
    # ---------------------------------------------------------

    dependency_graph = []

    for dependency in dependencies:
        source_name = service_map.get(
            dependency.source_service_id,
            "Unknown",
        )

        target_name = service_map.get(
            dependency.target_service_id,
            "Unknown",
        )

        dependency_graph.append(
            {
                "source_service": source_name,
                "target_service": target_name,
                "dependency_type": dependency.dependency_type,
            }
        )

    # ---------------------------------------------------------
    # 6. Calculate deterministic hypothesis scores
    # ---------------------------------------------------------

    hypothesis_results = []
    deployments_by_id = {
        str(deployment.id): deployment
        for deployment in deployments
    }
    events_by_id = {str(event.id): event for event in events}

    for hypothesis in hypotheses:
        evidence_items = (
            db.query(Evidence)
            .filter(Evidence.hypothesis_id == hypothesis.id)
            .order_by(Evidence.strength.desc())
            .all()
        )

        evidence_strengths = [evidence.strength for evidence in evidence_items]

        if evidence_strengths:
            average_evidence = sum(evidence_strengths) / len(
                evidence_strengths
            )
        else:
            average_evidence = 0

        # A temporal correlation supports a hypothesis only when the
        # hypothesis's own evidence cites the deployment or event involved.
        # Sharing a service with an incident-level correlation is not enough.
        evidence_source_ids = {
            str(evidence.source_id)
            for evidence in evidence_items
            if evidence.source_id is not None
        }
        temporal_candidates = []

        for correlation in temporal_correlations:
            if (
                correlation["deployment_id"] not in evidence_source_ids
                and correlation["event_id"] not in evidence_source_ids
            ):
                continue

            delay_minutes = correlation["delay_minutes"]
            if delay_minutes <= 5:
                correlation_score = 100
            elif delay_minutes <= 10:
                correlation_score = 80
            else:
                correlation_score = 60

            temporal_candidates.append(
                {
                    "correlation": correlation,
                    "score": correlation_score,
                }
            )

        # Choose one strongest relationship deterministically for scoring and
        # explanation; all candidates are already evidence-specific.
        temporal_candidates.sort(
            key=lambda candidate: (
                -candidate["score"],
                candidate["correlation"]["delay_minutes"],
                candidate["correlation"]["deployment_id"],
                candidate["correlation"]["event_id"],
            )
        )
        relevant_correlations = [
            candidate["correlation"]
            for candidate in temporal_candidates
        ]
        strongest_temporal = (
            temporal_candidates[0]
            if temporal_candidates
            else None
        )

        # Each component is normalized to 0-100 before applying its weight.
        # Five supporting evidence items are enough to reach the count cap.
        original_score = max(0, min(hypothesis.score, 100))
        evidence_score = max(0, min(average_evidence, 100))
        temporal_score = (
            strongest_temporal["score"]
            if strongest_temporal
            else 0
        )
        evidence_count_score = min(len(evidence_items) * 20, 100)

        # A dependency supports a hypothesis only when its service is one
        # endpoint and the other endpoint also appears in a temporal
        # correlation relevant to that hypothesis. This avoids assigning a
        # score merely because an unrelated dependency exists in the graph.
        correlated_service_ids = {
            deployments_by_id[correlation["deployment_id"]].service_id
            for correlation in relevant_correlations
        } | {
            events_by_id[correlation["event_id"]].service_id
            for correlation in relevant_correlations
        }
        relevant_dependencies = [
            dependency
            for dependency in dependencies
            if hypothesis.service_id is not None
            and (
                (
                    dependency.source_service_id == hypothesis.service_id
                    and dependency.target_service_id in correlated_service_ids
                )
                or (
                    dependency.target_service_id == hypothesis.service_id
                    and dependency.source_service_id in correlated_service_ids
                )
            )
        ]
        dependency_score = 100 if relevant_dependencies else 0

        # The complete scoring formula is deterministic and deliberately does
        # not use AI for ranking or probable-cause selection.
        final_score = round(
            (original_score * 0.30)
            + (evidence_score * 0.30)
            + (temporal_score * 0.25)
            + (dependency_score * 0.10)
            + (evidence_count_score * 0.05)
        )
        final_score = max(0, min(final_score, 100))

        if final_score >= 80:
            confidence = "high"
        elif final_score >= 60:
            confidence = "medium"
        else:
            confidence = "low"

        why = [
            f"Original hypothesis score: {original_score}/100.",
        ]

        if strongest_temporal:
            correlation = strongest_temporal["correlation"]
            related_event = events_by_id[correlation["event_id"]]
            why.append(
                "Temporal relationship: "
                f"{correlation['deployment_service']} deployment preceded "
                f"{related_event.message} by "
                f"{correlation['delay_minutes']:.1f} minutes."
            )

        for dependency in relevant_dependencies:
            why.append(
                "Dependency relationship: "
                f"{service_map.get(dependency.source_service_id, 'Unknown')} "
                f"depends on "
                f"{service_map.get(dependency.target_service_id, 'Unknown')} "
                f"({dependency.dependency_type})."
            )

        if evidence_items:
            strongest_evidence = evidence_items[0]
            why.append(
                "Strongest evidence "
                f"(strength {strongest_evidence.strength}): "
                f"{strongest_evidence.description}"
            )
            why.append(
                f"Supporting evidence items: {len(evidence_items)}."
            )

        hypothesis_results.append(
            {
                "id": str(hypothesis.id),
                "title": hypothesis.title,
                "description": hypothesis.description,
                "original_score": hypothesis.score,
                "evidence_count": len(evidence_items),
                "average_evidence_strength": round(
                    average_evidence,
                    2,
                ),
                "temporal_score": temporal_score,
                "dependency_score": dependency_score,
                "evidence_count_score": evidence_count_score,
                "final_score": final_score,
                "confidence": confidence,
                "status": hypothesis.status,
                "why": why,
                "evidence": [
                    {
                        "id": str(evidence.id),
                        "type": evidence.evidence_type,
                        "description": evidence.description,
                        "strength": evidence.strength,
                        "source_id": (
                            str(evidence.source_id)
                            if evidence.source_id
                            else None
                        ),
                    }
                    for evidence in evidence_items
                ],
            }
        )

    # ---------------------------------------------------------
    # 7. Rank hypotheses
    # ---------------------------------------------------------

    hypothesis_results.sort(
        key=lambda item: (
            -item["final_score"],
            -item["original_score"],
            item["id"],
        ),
    )

    # ---------------------------------------------------------
    # 8. Select probable cause
    # ---------------------------------------------------------

    probable_cause = None

    if hypothesis_results:
        top = hypothesis_results[0]

        probable_cause = {
            "hypothesis_id": top["id"],
            "title": top["title"],
            "score": top["final_score"],
            "confidence": top["confidence"],
            "reason": (
                "This hypothesis has the highest deterministic "
                "score based on its original score, evidence, temporal "
                "correlations, and dependency relationships."
            ),
        }

    # ---------------------------------------------------------
    # 9. Return complete analysis
    # ---------------------------------------------------------

    return {
        "incident_id": str(incident_id),
        "timeline": timeline_response,
        "temporal_correlations": temporal_correlations,
        "dependency_graph": dependency_graph,
        "hypotheses": hypothesis_results,
        "probable_cause": probable_cause,
    }
