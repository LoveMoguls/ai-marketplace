// Configuration
const DATA_BASE_URL = './data/';

// State
let allIdeas = [];
let allClusters = [];
let activeFilters = {
    strategic_area: new Set(),
    arch_pattern: new Set(),
    status: new Set(),
    has_pitch: null,
    enabler: null
};
let searchQuery = '';
let sortBy = 'value_desc';
let viewMode = 'grid';

// === Init ===

async function init() {
    try {
        const [ideasRes, clustersRes] = await Promise.all([
            fetch(DATA_BASE_URL + 'ideas.json'),
            fetch(DATA_BASE_URL + 'clusters.json')
        ]);

        if (ideasRes.ok) {
            allIdeas = await ideasRes.json();
        } else {
            allIdeas = [];
        }

        if (clustersRes.ok) {
            allClusters = await clustersRes.json();
        } else {
            allClusters = [];
        }
    } catch (e) {
        console.warn('Could not load data:', e);
        allIdeas = [];
        allClusters = [];
    }

    setupEventListeners();
    renderFilterBar();
    render();
}

function setupEventListeners() {
    document.getElementById('search-input').addEventListener('input', function (e) {
        searchQuery = e.target.value.trim().toLowerCase();
        render();
    });

    document.getElementById('sort-select').addEventListener('change', function (e) {
        sortBy = e.target.value;
        render();
    });

    document.querySelectorAll('.view-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            viewMode = btn.dataset.view;
            document.querySelectorAll('.view-btn').forEach(function (b) {
                b.classList.remove('active');
            });
            btn.classList.add('active');
            render();
        });
    });
}

// === Filtering ===

function getFilteredIdeas() {
    return allIdeas.filter(function (idea) {
        // Strategic area filter
        if (activeFilters.strategic_area.size > 0 && !activeFilters.strategic_area.has(idea.strategic_area)) {
            return false;
        }

        // Arch pattern filter
        if (activeFilters.arch_pattern.size > 0 && !activeFilters.arch_pattern.has(idea.arch_pattern)) {
            return false;
        }

        // Status filter
        if (activeFilters.status.size > 0 && !activeFilters.status.has(idea.status)) {
            return false;
        }

        // Has pitch filter
        if (activeFilters.has_pitch === true && (!idea.links || !idea.links.pitch_url)) {
            return false;
        }
        if (activeFilters.has_pitch === false && idea.links && idea.links.pitch_url) {
            return false;
        }

        // Enabler filter
        if (activeFilters.enabler === true && !idea.enabler_candidate) {
            return false;
        }
        if (activeFilters.enabler === false && idea.enabler_candidate) {
            return false;
        }

        // Search query
        if (searchQuery) {
            var haystack = [
                idea.title || '',
                idea.summary || '',
                idea.problem || ''
            ].join(' ').toLowerCase();
            if (haystack.indexOf(searchQuery) === -1) {
                return false;
            }
        }

        return true;
    });
}

// === Sorting ===

function getSortedIdeas(ideas) {
    var sorted = ideas.slice();
    if (sortBy === 'votes_desc') {
        sorted.sort(function (a, b) {
            return (b.upvotes || 0) - (a.upvotes || 0);
        });
    } else if (sortBy === 'value_desc') {
        sorted.sort(function (a, b) {
            var av = (a.scores && a.scores.business_value) || 0;
            var bv = (b.scores && b.scores.business_value) || 0;
            return bv - av;
        });
    } else if (sortBy === 'date_desc') {
        sorted.sort(function (a, b) {
            var ad = a.submitted_at || '';
            var bd = b.submitted_at || '';
            return bd.localeCompare(ad);
        });
    } else if (sortBy === 'alpha') {
        sorted.sort(function (a, b) {
            return (a.title || '').localeCompare(b.title || '');
        });
    }
    return sorted;
}

// === Render Stats ===

function renderStats(ideas) {
    var container = document.getElementById('stats-bar');
    var total = ideas.length;
    var inProd = ideas.filter(function (i) { return i.status === 'In production'; }).length;
    var enablers = ideas.filter(function (i) { return i.enabler_candidate; }).length;
    var clusters = new Set(ideas.map(function (i) { return i.cluster_id; }).filter(function (id) { return id != null; })).size;

    container.innerHTML =
        '<div class="stat-card"><div class="stat-value">' + total + '</div><div class="stat-label">Total Ideas</div></div>' +
        '<div class="stat-card"><div class="stat-value">' + inProd + '</div><div class="stat-label">In Production</div></div>' +
        '<div class="stat-card"><div class="stat-value">' + enablers + '</div><div class="stat-label">Enablers</div></div>' +
        '<div class="stat-card"><div class="stat-value">' + clusters + '</div><div class="stat-label">Clusters</div></div>';
}

// === Render Filter Bar ===

function renderFilterBar() {
    var container = document.getElementById('filter-bar');
    container.innerHTML = '';

    // Extract unique values
    var strategicAreas = getUniqueValues('strategic_area');
    var archPatterns = getUniqueValues('arch_pattern');
    var statuses = getUniqueValues('status');

    // Strategic Area group
    if (strategicAreas.length > 0) {
        container.appendChild(buildFilterGroup('Area', 'strategic_area', strategicAreas));
        container.appendChild(createSeparator());
    }

    // Arch Pattern group
    if (archPatterns.length > 0) {
        container.appendChild(buildFilterGroup('Pattern', 'arch_pattern', archPatterns));
        container.appendChild(createSeparator());
    }

    // Status group
    if (statuses.length > 0) {
        container.appendChild(buildFilterGroup('Status', 'status', statuses));
        container.appendChild(createSeparator());
    }

    // Toggle pills
    var toggleGroup = document.createElement('div');
    toggleGroup.className = 'filter-group';

    var pitchPill = document.createElement('button');
    pitchPill.className = 'filter-pill' + (activeFilters.has_pitch === true ? ' active' : '');
    pitchPill.textContent = 'Has Pitch';
    pitchPill.addEventListener('click', function () {
        activeFilters.has_pitch = activeFilters.has_pitch === true ? null : true;
        renderFilterBar();
        render();
    });
    toggleGroup.appendChild(pitchPill);

    var enablerPill = document.createElement('button');
    enablerPill.className = 'filter-pill' + (activeFilters.enabler === true ? ' active' : '');
    enablerPill.textContent = 'Enabler Candidate';
    enablerPill.addEventListener('click', function () {
        activeFilters.enabler = activeFilters.enabler === true ? null : true;
        renderFilterBar();
        render();
    });
    toggleGroup.appendChild(enablerPill);

    container.appendChild(toggleGroup);
}

function getUniqueValues(field) {
    var values = new Set();
    allIdeas.forEach(function (idea) {
        if (idea[field]) {
            values.add(idea[field]);
        }
    });
    return Array.from(values).sort();
}

function buildFilterGroup(label, filterKey, values) {
    var group = document.createElement('div');
    group.className = 'filter-group';

    var labelEl = document.createElement('span');
    labelEl.className = 'filter-group-label';
    labelEl.textContent = label;
    group.appendChild(labelEl);

    values.forEach(function (value) {
        var pill = document.createElement('button');
        pill.className = 'filter-pill' + (activeFilters[filterKey].has(value) ? ' active' : '');
        pill.textContent = value;
        pill.addEventListener('click', function () {
            if (activeFilters[filterKey].has(value)) {
                activeFilters[filterKey].delete(value);
            } else {
                activeFilters[filterKey].add(value);
            }
            renderFilterBar();
            render();
        });
        group.appendChild(pill);
    });

    return group;
}

function createSeparator() {
    var sep = document.createElement('div');
    sep.className = 'filter-separator';
    return sep;
}

// === Render Cards ===

function renderCards(ideas) {
    var container = document.getElementById('cards-container');
    container.innerHTML = '';

    if (ideas.length === 0) {
        container.innerHTML =
            '<div class="empty-state">' +
            '<div class="empty-icon">&#128269;</div>' +
            '<div class="empty-title">No ideas found</div>' +
            '<div class="empty-text">Try adjusting your filters or search query.</div>' +
            '</div>';
        return;
    }

    var grid = document.createElement('div');
    grid.className = 'card-grid';

    ideas.forEach(function (idea) {
        grid.appendChild(buildCard(idea));
    });

    container.appendChild(grid);
}

// === Render Cluster View ===

function renderClusterView(ideas) {
    var container = document.getElementById('cards-container');
    container.innerHTML = '';

    if (ideas.length === 0) {
        container.innerHTML =
            '<div class="empty-state">' +
            '<div class="empty-icon">&#128269;</div>' +
            '<div class="empty-title">No ideas found</div>' +
            '<div class="empty-text">Try adjusting your filters or search query.</div>' +
            '</div>';
        return;
    }

    // Group ideas by cluster_id
    var groups = {};
    var unclustered = [];

    ideas.forEach(function (idea) {
        if (idea.cluster_id != null) {
            if (!groups[idea.cluster_id]) {
                groups[idea.cluster_id] = [];
            }
            groups[idea.cluster_id].push(idea);
        } else {
            unclustered.push(idea);
        }
    });

    // Render each cluster
    Object.keys(groups).sort(function (a, b) { return Number(a) - Number(b); }).forEach(function (clusterId) {
        var clusterIdeas = groups[clusterId];
        var clusterMeta = allClusters.find(function (c) { return c.id === Number(clusterId); });

        var section = document.createElement('div');
        section.className = 'cluster-section';

        // Cluster header
        var header = document.createElement('div');
        header.className = 'cluster-header';

        var label = document.createElement('div');
        label.className = 'cluster-label';
        label.textContent = clusterMeta ? clusterMeta.label : 'Cluster ' + clusterId;
        header.appendChild(label);

        if (clusterMeta && clusterMeta.description) {
            var desc = document.createElement('div');
            desc.className = 'cluster-description';
            desc.textContent = clusterMeta.description;
            header.appendChild(desc);
        }

        if (clusterMeta && clusterMeta.shared_components && clusterMeta.shared_components.length > 0) {
            var shared = document.createElement('div');
            shared.className = 'cluster-shared';
            var sharedLabel = document.createElement('span');
            sharedLabel.className = 'cluster-shared-label';
            sharedLabel.textContent = 'Shared:';
            shared.appendChild(sharedLabel);

            clusterMeta.shared_components.forEach(function (comp) {
                var tag = document.createElement('span');
                tag.className = 'tech-tag';
                tag.textContent = comp;
                shared.appendChild(tag);
            });
            header.appendChild(shared);
        }

        section.appendChild(header);

        // Cards grid within cluster
        var grid = document.createElement('div');
        grid.className = 'card-grid';
        clusterIdeas.forEach(function (idea) {
            grid.appendChild(buildCard(idea));
        });
        section.appendChild(grid);

        container.appendChild(section);
    });

    // Unclustered ideas
    if (unclustered.length > 0) {
        var section = document.createElement('div');
        section.className = 'cluster-section';

        var header = document.createElement('div');
        header.className = 'cluster-header';
        var label = document.createElement('div');
        label.className = 'cluster-label';
        label.textContent = 'Unclustered';
        header.appendChild(label);
        section.appendChild(header);

        var grid = document.createElement('div');
        grid.className = 'card-grid';
        unclustered.forEach(function (idea) {
            grid.appendChild(buildCard(idea));
        });
        section.appendChild(grid);

        container.appendChild(section);
    }
}

// === Build Card ===

function buildCard(idea) {
    var card = document.createElement('div');
    card.className = 'card';

    // Header
    var header = document.createElement('div');
    header.className = 'card-header';

    var title = document.createElement('div');
    title.className = 'card-title';
    title.textContent = idea.title || 'Untitled';
    header.appendChild(title);

    var statusBadge = document.createElement('span');
    statusBadge.className = 'badge ' + getStatusClass(idea.status);
    statusBadge.textContent = idea.status || 'Unknown';
    header.appendChild(statusBadge);

    if (idea.enabler_candidate) {
        var enablerBadge = document.createElement('span');
        enablerBadge.className = 'badge badge-enabler';
        enablerBadge.textContent = 'Enabler';
        header.appendChild(enablerBadge);
    }

    card.appendChild(header);

    // Body
    var body = document.createElement('div');
    body.className = 'card-body';

    // Two sections: Business + Engineering
    var sections = document.createElement('div');
    sections.className = 'card-sections';

    // Business section
    var bizSection = document.createElement('div');
    bizSection.className = 'card-section';

    var bizLabel = document.createElement('div');
    bizLabel.className = 'section-label';
    bizLabel.textContent = 'Business';
    bizSection.appendChild(bizLabel);

    if (idea.strategic_area) {
        var areaField = document.createElement('div');
        areaField.className = 'section-field';
        areaField.innerHTML = '<span class="field-label">Area</span><span class="field-value">' + escapeHtml(idea.strategic_area) + '</span>';
        bizSection.appendChild(areaField);
    }

    if (idea.business_stakeholder) {
        var stakeholderField = document.createElement('div');
        stakeholderField.className = 'section-field';
        stakeholderField.innerHTML = '<span class="field-label">Stakeholder</span><span class="field-value">' + escapeHtml(idea.business_stakeholder) + '</span>';
        bizSection.appendChild(stakeholderField);
    }

    if (idea.business_value) {
        var valueText = document.createElement('div');
        valueText.className = 'value-text';
        valueText.textContent = idea.business_value;
        bizSection.appendChild(valueText);
    }

    sections.appendChild(bizSection);

    // Engineering section
    var engSection = document.createElement('div');
    engSection.className = 'card-section';

    var engLabel = document.createElement('div');
    engLabel.className = 'section-label';
    engLabel.textContent = 'Engineering';
    engSection.appendChild(engLabel);

    if (idea.arch_pattern) {
        var archField = document.createElement('div');
        archField.className = 'section-field';
        var archBadge = document.createElement('span');
        archBadge.className = 'arch-badge';
        archBadge.textContent = idea.arch_pattern;
        archField.appendChild(archBadge);
        engSection.appendChild(archField);
    }

    if (idea.tech_components && idea.tech_components.length > 0) {
        var tags = document.createElement('div');
        tags.className = 'tech-tags';
        idea.tech_components.forEach(function (comp) {
            var tag = document.createElement('span');
            tag.className = 'tech-tag';
            tag.textContent = comp;
            tags.appendChild(tag);
        });
        engSection.appendChild(tags);
    }

    sections.appendChild(engSection);
    body.appendChild(sections);

    // Scores
    if (idea.scores) {
        var scoresRow = document.createElement('div');
        scoresRow.className = 'scores-row';

        if (idea.scores.business_value != null) {
            var bvGroup = document.createElement('div');
            bvGroup.className = 'score-group';
            var bvLabel = document.createElement('span');
            bvLabel.className = 'score-label';
            bvLabel.textContent = 'Value';
            bvGroup.appendChild(bvLabel);
            bvGroup.appendChild(renderPips(idea.scores.business_value, 10));
            scoresRow.appendChild(bvGroup);
        }

        if (idea.scores.feasibility != null) {
            var feasGroup = document.createElement('div');
            feasGroup.className = 'score-group';
            var feasLabel = document.createElement('span');
            feasLabel.className = 'score-label';
            feasLabel.textContent = 'Feasibility';
            feasGroup.appendChild(feasLabel);
            feasGroup.appendChild(renderPips(idea.scores.feasibility, 6));
            scoresRow.appendChild(feasGroup);
        }

        body.appendChild(scoresRow);
    }

    // Links
    var links = document.createElement('div');
    links.className = 'card-links';

    var pitchUrl = idea.links && idea.links.pitch_url;
    var repoUrl = idea.links && idea.links.repo_url;
    var docsUrl = idea.links && idea.links.docs_url;

    if (pitchUrl) {
        var pitchChip = document.createElement('a');
        pitchChip.className = 'link-chip chip-pitch';
        pitchChip.href = pitchUrl;
        pitchChip.target = '_blank';
        pitchChip.rel = 'noopener';
        pitchChip.textContent = 'Pitch';
        links.appendChild(pitchChip);
    } else {
        var pitchEmpty = document.createElement('span');
        pitchEmpty.className = 'link-chip chip-empty';
        pitchEmpty.textContent = 'Pitch N/A';
        links.appendChild(pitchEmpty);
    }

    if (repoUrl) {
        var repoChip = document.createElement('a');
        repoChip.className = 'link-chip chip-repo';
        repoChip.href = repoUrl;
        repoChip.target = '_blank';
        repoChip.rel = 'noopener';
        repoChip.textContent = 'Repo';
        links.appendChild(repoChip);
    } else {
        var repoEmpty = document.createElement('span');
        repoEmpty.className = 'link-chip chip-empty';
        repoEmpty.textContent = 'Repo N/A';
        links.appendChild(repoEmpty);
    }

    if (docsUrl) {
        var docsChip = document.createElement('a');
        docsChip.className = 'link-chip chip-docs';
        docsChip.href = docsUrl;
        docsChip.target = '_blank';
        docsChip.rel = 'noopener';
        docsChip.textContent = 'Docs';
        links.appendChild(docsChip);
    } else {
        var docsEmpty = document.createElement('span');
        docsEmpty.className = 'link-chip chip-empty';
        docsEmpty.textContent = 'Docs N/A';
        links.appendChild(docsEmpty);
    }

    body.appendChild(links);
    card.appendChild(body);

    // Footer
    var footer = document.createElement('div');
    footer.className = 'card-footer';

    var avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = getInitials(idea.submitted_by);
    footer.appendChild(avatar);

    var contactInfo = document.createElement('div');
    contactInfo.className = 'contact-info';

    var contactName = document.createElement('div');
    contactName.className = 'contact-name';
    contactName.textContent = idea.submitted_by || 'Unknown';
    contactInfo.appendChild(contactName);

    if (idea.contact_email) {
        var contactEmail = document.createElement('div');
        contactEmail.className = 'contact-email';
        contactEmail.textContent = idea.contact_email;
        contactInfo.appendChild(contactEmail);
    }

    footer.appendChild(contactInfo);

    // Upvote button
    var upvoteCount = idea.upvotes || 0;
    var upvoteEl = document.createElement('a');
    upvoteEl.className = 'upvote-btn' + (upvoteCount > 0 ? ' has-votes' : '');
    upvoteEl.title = idea.issue_url ? 'Vote with a thumbs-up on the GitHub Issue' : 'Upvotes';
    if (idea.issue_url) {
        upvoteEl.href = idea.issue_url;
        upvoteEl.target = '_blank';
        upvoteEl.rel = 'noopener';
    }
    upvoteEl.innerHTML = '<span class="upvote-icon">&#9650;</span><span class="upvote-count">' + upvoteCount + '</span>';
    footer.appendChild(upvoteEl);

    if (idea.cluster_label) {
        var clusterTag = document.createElement('span');
        clusterTag.className = 'cluster-tag';
        clusterTag.textContent = idea.cluster_label;
        footer.appendChild(clusterTag);
    }

    card.appendChild(footer);

    return card;
}

// === Helpers ===

function getInitials(name) {
    if (!name) return '?';
    var parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0][0].toUpperCase();
}

function getStatusClass(status) {
    if (!status) return 'badge-new';
    var s = status.toLowerCase();
    if (s === 'in production' || s === 'in prod') return 'badge-prod';
    if (s === 'in development') return 'badge-dev';
    if (s === 'under review') return 'badge-review';
    return 'badge-new';
}

function renderPips(score, max) {
    var container = document.createElement('div');
    container.className = 'pips';
    for (var i = 0; i < max; i++) {
        var pip = document.createElement('div');
        pip.className = 'pip';
        if (i < score) {
            pip.classList.add('filled');
            if (max <= 6) {
                // Feasibility: color by level
                if (score >= 4) pip.classList.add('high');
                else if (score <= 2) pip.classList.add('low');
            } else {
                // Business value: color by level
                if (score >= 7) pip.classList.add('high');
                else if (score <= 3) pip.classList.add('low');
            }
        }
        container.appendChild(pip);
    }
    return container;
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// === Main Render ===

function render() {
    var filtered = getFilteredIdeas();
    var sorted = getSortedIdeas(filtered);
    renderStats(sorted);
    if (viewMode === 'cluster') {
        renderClusterView(sorted);
    } else {
        renderCards(sorted);
    }
}

// === Bootstrap ===
document.addEventListener('DOMContentLoaded', init);
