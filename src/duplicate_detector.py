"""
Duplicate requirement detection using semantic similarity.

Compares new requirements against existing backlog to find:
- Duplicates (same intent, different wording)
- Near-duplicates (overlapping scope)
- Conflicting requirements (contradictory goals)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class MatchType(str, Enum):
    """Type of match found between requirements."""
    DUPLICATE = "duplicate"
    NEAR_DUPLICATE = "near_duplicate"
    CONFLICTING = "conflicting"
    RELATED = "related"


@dataclass
class RequirementMatch:
    """A match between the new requirement and an existing one."""
    issue_key: str
    title: str
    match_type: MatchType
    confidence: float
    reason: str


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    # Lowercase, remove extra whitespace
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    # Remove common filler words for better matching
    return text


def _extract_key_phrases(text: str) -> set:
    """Extract key phrases/concepts from text."""
    normalized = _normalize_text(text)
    
    # Split into words
    words = set(normalized.split())
    
    # Remove very common words but keep domain-relevant terms
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
        'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'under', 'again', 'further', 'then', 'once', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or',
        'because', 'until', 'while', 'this', 'that', 'these', 'those', 'i',
        'we', 'you', 'he', 'she', 'it', 'they', 'what', 'which', 'who',
        'feature', 'want', 'able', 'their', 'new', 'using', 'via', 'allow',
        'allowing', 'should', 'functionality', 'implement', 'create', 'build'
    }
    
    return words - stop_words


def _get_synonyms(word: str) -> set:
    """Get common synonyms for requirement-related words."""
    synonym_groups = [
        {'login', 'signin', 'sign-in', 'authenticate', 'authentication', 'log-in'},
        {'logout', 'signout', 'sign-out', 'log-out'},
        {'create', 'add', 'make', 'build', 'implement', 'develop'},
        {'update', 'edit', 'modify', 'change', 'revise'},
        {'delete', 'remove', 'erase', 'drop'},
        {'view', 'display', 'show', 'see', 'list'},
        {'user', 'users', 'customer', 'customers', 'member', 'members'},
        {'password', 'passwords', 'credential', 'credentials', 'pass'},
        {'email', 'emails', 'e-mail', 'mail'},
        {'profile', 'profiles', 'account', 'accounts'},
        {'reset', 'restore', 'recover', 'recovery'},
        {'notification', 'notifications', 'notify', 'alert', 'alerts'},
        {'automatic', 'auto', 'automatically'},
        {'enable', 'enabled', 'activate', 'turn-on'},
        {'disable', 'disabled', 'deactivate', 'turn-off'},
        {'export', 'download', 'extract'},
        {'import', 'upload', 'load'},
        {'data', 'information', 'info'},
        {'dashboard', 'panel', 'overview'},
    ]
    
    result = {word}
    for group in synonym_groups:
        if word in group:
            result.update(group)
    return result


def _calculate_jaccard_similarity(set1: set, set2: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def _extract_action_object_pairs(text: str) -> List[tuple]:
    """Extract action-object pairs that represent intent."""
    normalized = _normalize_text(text)
    
    # Common action verbs in requirements
    actions = [
        'create', 'add', 'implement', 'build', 'develop', 'make',
        'update', 'modify', 'change', 'edit', 'revise',
        'delete', 'remove', 'disable', 'hide',
        'view', 'display', 'show', 'list', 'see',
        'search', 'filter', 'sort', 'find',
        'export', 'import', 'download', 'upload',
        'send', 'receive', 'notify', 'alert',
        'login', 'logout', 'authenticate', 'authorize',
        'manage', 'configure', 'setup', 'set'
    ]
    
    pairs = []
    words = normalized.split()
    
    for i, word in enumerate(words):
        if word in actions and i + 1 < len(words):
            # Get the next few words as the object
            obj_words = words[i+1:min(i+4, len(words))]
            obj = ' '.join(obj_words)
            pairs.append((word, obj))
    
    return pairs


def _expand_with_synonyms(words: set) -> set:
    """Expand a set of words with their synonyms."""
    expanded = set()
    for word in words:
        expanded.update(_get_synonyms(word))
    return expanded


def _semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two texts.
    
    Uses a combination of:
    - Key phrase overlap (Jaccard) with synonym expansion
    - Word overlap ratio
    - Common domain term detection
    """
    if not text1 or not text2:
        return 0.0
    
    # Extract key phrases
    phrases1 = _extract_key_phrases(text1)
    phrases2 = _extract_key_phrases(text2)
    
    if not phrases1 or not phrases2:
        return 0.0
    
    # Direct overlap
    direct_intersection = phrases1 & phrases2
    direct_sim = len(direct_intersection) / min(len(phrases1), len(phrases2)) if phrases1 and phrases2 else 0
    
    # Synonym-expanded overlap
    expanded1 = _expand_with_synonyms(phrases1)
    expanded2 = _expand_with_synonyms(phrases2)
    expanded_intersection = expanded1 & expanded2
    expanded_sim = len(expanded_intersection) / min(len(expanded1), len(expanded2)) if expanded1 and expanded2 else 0
    
    # Jaccard similarity on expanded sets
    jaccard_sim = _calculate_jaccard_similarity(expanded1, expanded2)
    
    # Weighted combination favoring direct and synonym matches
    similarity = 0.4 * direct_sim + 0.35 * expanded_sim + 0.25 * jaccard_sim
    
    # Boost if there are multiple direct matches
    if len(direct_intersection) >= 3:
        similarity = min(1.0, similarity * 1.3)
    elif len(direct_intersection) >= 2:
        similarity = min(1.0, similarity * 1.15)
    
    return similarity


def _detect_conflict(text1: str, text2: str) -> bool:
    """Detect if two requirements might be conflicting."""
    normalized1 = _normalize_text(text1)
    normalized2 = _normalize_text(text2)
    
    # Look for opposing action patterns
    opposing_pairs = [
        ('enable', 'disable'),
        ('enabled', 'disabled'),
        ('show', 'hide'),
        ('showing', 'hiding'),
        ('add', 'remove'),
        ('allow', 'prevent'),
        ('allow', 'block'),
        ('require', 'optional'),
        ('mandatory', 'optional'),
        ('always', 'never'),
        ('automatic', 'manual'),
        ('automatically', 'manually'),
        ('visible', 'hidden'),
        ('public', 'private'),
        ('include', 'exclude'),
    ]
    
    # Check for opposing words in the texts
    for word1, word2 in opposing_pairs:
        has_word1_in_text1 = word1 in normalized1
        has_word2_in_text1 = word2 in normalized1
        has_word1_in_text2 = word1 in normalized2
        has_word2_in_text2 = word2 in normalized2
        
        # One text has word1, other has word2
        if (has_word1_in_text1 and has_word2_in_text2) or \
           (has_word2_in_text1 and has_word1_in_text2):
            # Check if they're talking about similar topics
            phrases1 = _extract_key_phrases(text1)
            phrases2 = _extract_key_phrases(text2)
            
            # Expand with synonyms for better topic matching
            expanded1 = _expand_with_synonyms(phrases1)
            expanded2 = _expand_with_synonyms(phrases2)
            
            overlap = len(expanded1 & expanded2)
            if overlap >= 2:  # At least 2 common topics
                return True
    
    return False


def _generate_match_reason(
    new_req: str,
    existing_req: str,
    match_type: MatchType,
    confidence: float
) -> str:
    """Generate a human-readable reason for the match."""
    phrases_new = _extract_key_phrases(new_req)
    phrases_existing = _extract_key_phrases(existing_req)
    common = phrases_new & phrases_existing
    
    if match_type == MatchType.DUPLICATE:
        if common:
            return f"Both requirements address the same functionality: {', '.join(list(common)[:5])}"
        return "Requirements describe the same intent with different wording"
    
    elif match_type == MatchType.NEAR_DUPLICATE:
        if common:
            return f"Significant overlap in scope: {', '.join(list(common)[:5])}"
        return "Requirements have overlapping scope and may need consolidation"
    
    elif match_type == MatchType.CONFLICTING:
        return "Requirements may have contradictory goals - review needed"
    
    else:  # RELATED
        if common:
            return f"Related topics: {', '.join(list(common)[:3])}"
        return "Requirements touch on related areas"


def find_duplicates(
    new_issue_key: Optional[str],
    new_title: str,
    new_description: str,
    candidates: List[dict],
    threshold: float = 0.5
) -> dict:
    """
    Find duplicate or related requirements in the candidate list.
    
    Args:
        new_issue_key: Key of the new issue (to exclude from comparison)
        new_title: Title of the new requirement
        new_description: Description of the new requirement
        candidates: List of candidate issues, each with 'key', 'title', 'description'
        threshold: Minimum similarity threshold for matches (default 0.5)
    
    Returns:
        Dict with duplicates_found, top_matches, and analysis summary
    """
    new_text = f"{new_title} {new_description}"
    matches: List[RequirementMatch] = []
    
    for candidate in candidates:
        candidate_key = candidate.get('key', candidate.get('issue_key', ''))
        
        # Skip self-comparison
        if new_issue_key and candidate_key == new_issue_key:
            continue
        
        candidate_title = candidate.get('title', candidate.get('summary', ''))
        candidate_desc = candidate.get('description', '')
        candidate_text = f"{candidate_title} {candidate_desc}"
        
        # Calculate similarity
        similarity = _semantic_similarity(new_text, candidate_text)
        
        # Check for conflicts
        is_conflict = _detect_conflict(new_text, candidate_text)
        
        # Determine match type
        if is_conflict and similarity > 0.3:
            match_type = MatchType.CONFLICTING
            confidence = min(0.9, similarity + 0.2)
        elif similarity >= 0.8:
            match_type = MatchType.DUPLICATE
            confidence = similarity
        elif similarity >= 0.6:
            match_type = MatchType.NEAR_DUPLICATE
            confidence = similarity
        elif similarity >= threshold:
            match_type = MatchType.RELATED
            confidence = similarity
        else:
            continue  # Below threshold
        
        reason = _generate_match_reason(
            new_text, candidate_text, match_type, confidence
        )
        
        matches.append(RequirementMatch(
            issue_key=candidate_key,
            title=candidate_title,
            match_type=match_type,
            confidence=round(confidence, 2),
            reason=reason
        ))
    
    # Sort by confidence descending
    matches.sort(key=lambda m: m.confidence, reverse=True)
    
    # Prepare response
    duplicates = [m for m in matches if m.match_type == MatchType.DUPLICATE]
    near_duplicates = [m for m in matches if m.match_type == MatchType.NEAR_DUPLICATE]
    conflicts = [m for m in matches if m.match_type == MatchType.CONFLICTING]
    
    return {
        "duplicates_found": len(duplicates) > 0,
        "probable_duplicates_count": len(duplicates),
        "near_duplicates_count": len(near_duplicates),
        "conflicts_count": len(conflicts),
        "top_matches": [
            {
                "issue_key": m.issue_key,
                "title": m.title,
                "match_type": m.match_type.value,
                "confidence": m.confidence,
                "reason": m.reason
            }
            for m in matches[:10]  # Top 10 matches
        ],
        "recommendation": _get_recommendation(duplicates, near_duplicates, conflicts)
    }


def _get_recommendation(
    duplicates: List[RequirementMatch],
    near_duplicates: List[RequirementMatch],
    conflicts: List[RequirementMatch]
) -> str:
    """Generate a recommendation based on the matches found."""
    if duplicates:
        keys = [d.issue_key for d in duplicates[:3]]
        return f"PROBABLE DUPLICATE: Review {', '.join(keys)} before proceeding. Consider closing as duplicate."
    
    if conflicts:
        keys = [c.issue_key for c in conflicts[:3]]
        return f"CONFLICTING REQUIREMENTS: {', '.join(keys)} may have contradictory goals. Resolve conflicts before implementation."
    
    if near_duplicates:
        keys = [n.issue_key for n in near_duplicates[:3]]
        return f"OVERLAPPING SCOPE: Consider consolidating with {', '.join(keys)} to avoid redundant work."
    
    return "No significant duplicates found. Proceed with normal workflow."
