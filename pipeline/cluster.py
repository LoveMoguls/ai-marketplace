"""Clustering and enabler detection for AI marketplace ideas."""

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# Lazy singleton for sentence-transformers model.
_model = None


def _get_model():
    """Load sentence-transformers model as a lazy singleton."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model all-MiniLM-L6-v2")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def detect_enablers(ideas: list[dict]) -> list[dict]:
    """Mark ideas as enabler candidates if they share tech components.

    A component is "shared" when it appears in >= 2 ideas.  Ideas that
    contain at least one shared component get ``enabler_candidate = True``.

    Args:
        ideas: List of idea dicts, each with a ``tech_components`` list.

    Returns:
        The same list with ``enabler_candidate`` updated in-place.
    """
    component_counts: Counter = Counter()
    for idea in ideas:
        for comp in idea.get("tech_components", []):
            component_counts[comp] += 1

    shared = {comp for comp, count in component_counts.items() if count >= 2}
    logger.debug("Shared components (%d): %s", len(shared), shared)

    for idea in ideas:
        idea_comps = set(idea.get("tech_components", []))
        idea["enabler_candidate"] = bool(idea_comps & shared)

    return ideas


def _label_clusters_with_claude(
    clusters: list[dict[str, Any]],
    ideas: list[dict],
) -> list[dict[str, Any]]:
    """Use Claude API to generate a label and description for each cluster.

    Falls back to generic labels on any error.

    Args:
        clusters: List of cluster metadata dicts (id, idea_ids, shared_components).
        ideas: Full list of idea dicts for context.

    Returns:
        Clusters with ``label`` and ``description`` fields populated.
    """
    try:
        import anthropic

        client = anthropic.Anthropic()

        # Build a summary of each cluster for Claude.
        cluster_summaries = []
        ideas_by_id = {idea["id"]: idea for idea in ideas}
        for cluster in clusters:
            idea_titles = []
            idea_summaries = []
            for idea_id in cluster["idea_ids"]:
                idea = ideas_by_id.get(idea_id, {})
                idea_titles.append(idea.get("title", idea_id))
                idea_summaries.append(idea.get("summary", idea.get("title", idea_id)))
            cluster_summaries.append(
                f"Cluster {cluster['id']}:\n"
                f"  Ideas: {', '.join(idea_titles)}\n"
                f"  Shared components: {', '.join(cluster['shared_components'])}\n"
                f"  Summaries: {'; '.join(idea_summaries)}"
            )

        prompt = (
            "For each cluster below, generate:\n"
            "1. A kebab-case label (e.g. 'document-intelligence')\n"
            "2. A one-sentence description\n\n"
            "Return ONLY lines in this exact format, one per cluster:\n"
            "CLUSTER <id>|<kebab-label>|<one sentence description>\n\n"
            + "\n\n".join(cluster_summaries)
        )

        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        logger.debug("Claude cluster labels response: %s", response_text)

        # Parse response lines.
        labels: dict[int, tuple[str, str]] = {}
        for line in response_text.strip().splitlines():
            line = line.strip()
            if line.startswith("CLUSTER "):
                parts = line[len("CLUSTER "):].split("|", 2)
                if len(parts) == 3:
                    cid = int(parts[0].strip())
                    labels[cid] = (parts[1].strip(), parts[2].strip())

        for cluster in clusters:
            if cluster["id"] in labels:
                cluster["label"] = labels[cluster["id"]][0]
                cluster["description"] = labels[cluster["id"]][1]
            else:
                cluster["label"] = f"cluster-{cluster['id']}"
                cluster["description"] = f"Cluster {cluster['id']} of related ideas."

    except Exception:
        logger.warning("Claude API call for cluster labels failed, using fallback labels", exc_info=True)
        for cluster in clusters:
            cluster["label"] = f"cluster-{cluster['id']}"
            cluster["description"] = f"Cluster {cluster['id']} of related ideas."

    return clusters


def cluster_ideas(ideas: list[dict]) -> tuple[list[dict], list[dict]]:
    """Cluster ideas by semantic similarity and detect enablers.

    Uses sentence-transformers embeddings and KMeans clustering.
    Calls Claude API to generate human-readable cluster labels.

    Args:
        ideas: List of idea dicts with at least ``id``, ``summary`` or
               ``title``, and ``tech_components``.

    Returns:
        A tuple of (updated_ideas, clusters_list) where ideas have
        ``cluster_id`` and ``cluster_label`` set, and clusters_list
        contains cluster metadata.
    """
    if len(ideas) < 2:
        logger.info("Fewer than 2 ideas, assigning all to cluster 0")
        for idea in ideas:
            idea["cluster_id"] = 0
            idea["cluster_label"] = "unclustered"
        clusters = [{
            "id": 0,
            "label": "unclustered",
            "idea_ids": [idea["id"] for idea in ideas],
            "shared_components": [],
            "description": "Too few ideas to cluster.",
        }] if ideas else []
        detect_enablers(ideas)
        return ideas, clusters

    import numpy as np
    from sklearn.cluster import KMeans

    model = _get_model()

    # Generate embeddings from summaries (fallback to title).
    texts = [
        idea.get("summary") or idea.get("title", "")
        for idea in ideas
    ]
    logger.info("Generating embeddings for %d ideas", len(texts))
    embeddings = model.encode(texts)

    # Determine k.
    k = max(2, min(10, len(ideas) // 5))
    logger.info("Running KMeans with k=%d on %d ideas", k, len(ideas))

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Assign cluster_id to each idea.
    for idea, label in zip(ideas, labels):
        idea["cluster_id"] = int(label)

    # Build cluster metadata.
    clusters: list[dict[str, Any]] = []
    for cid in range(k):
        cluster_ideas_list = [idea for idea in ideas if idea["cluster_id"] == cid]
        idea_ids = [idea["id"] for idea in cluster_ideas_list]

        # Find shared components within this cluster.
        comp_counter: Counter = Counter()
        for idea in cluster_ideas_list:
            for comp in idea.get("tech_components", []):
                comp_counter[comp] += 1
        shared_comps = [comp for comp, count in comp_counter.items() if count >= 2]

        clusters.append({
            "id": cid,
            "label": f"cluster-{cid}",
            "idea_ids": idea_ids,
            "shared_components": shared_comps,
            "description": "",
        })

    # Use Claude to generate labels and descriptions.
    clusters = _label_clusters_with_claude(clusters, ideas)

    # Set cluster_label on each idea.
    cluster_labels = {c["id"]: c["label"] for c in clusters}
    for idea in ideas:
        idea["cluster_label"] = cluster_labels.get(idea["cluster_id"], f"cluster-{idea['cluster_id']}")

    # Detect enablers across all ideas.
    detect_enablers(ideas)

    logger.info(
        "Clustering complete: %d ideas in %d clusters, %d enabler candidates",
        len(ideas),
        len(clusters),
        sum(1 for i in ideas if i.get("enabler_candidate")),
    )

    return ideas, clusters
