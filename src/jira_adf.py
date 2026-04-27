"""
Jira Atlassian Document Format (ADF) extraction.

Converts ADF JSON (used by Jira Cloud for rich text) to plain text.
"""

import json
from typing import Union


def extract_text_from_adf(adf: Union[dict, str, None]) -> str:
    """
    Extract plain text from Jira Atlassian Document Format (ADF).
    
    Args:
        adf: ADF document as dict, JSON string, or None.
             If already a plain string (not JSON), returns it as-is.
    
    Returns:
        Plain text extracted from the ADF document.
    
    Examples:
        >>> extract_text_from_adf(None)
        ''
        >>> extract_text_from_adf("plain text")
        'plain text'
        >>> extract_text_from_adf({"type": "doc", "content": [...]})
        'extracted text...'
    """
    if adf is None:
        return ""
    
    if isinstance(adf, str):
        # Try to parse as JSON
        adf_stripped = adf.strip()
        if not adf_stripped:
            return ""
        
        # Check if it looks like JSON (starts with { or [)
        if adf_stripped.startswith('{') or adf_stripped.startswith('['):
            try:
                adf = json.loads(adf_stripped)
            except json.JSONDecodeError:
                # Not valid JSON, return as plain text
                return adf
        else:
            # Plain text string
            return adf
    
    if not isinstance(adf, dict):
        return str(adf) if adf else ""
    
    return _extract_node_text(adf)


def _extract_node_text(node: dict, list_prefix: str = "") -> str:
    """
    Recursively extract text from an ADF node.
    
    Args:
        node: ADF node dictionary
        list_prefix: Prefix for list items (bullet or number)
    
    Returns:
        Extracted text from the node and its children
    """
    if not isinstance(node, dict):
        return ""
    
    node_type = node.get("type", "")
    content = node.get("content", [])
    
    # Handle different node types
    if node_type == "doc":
        return _process_content(content)
    
    elif node_type == "paragraph":
        text = _process_content(content)
        return text + "\n" if text else ""
    
    elif node_type == "text":
        return node.get("text", "")
    
    elif node_type == "heading":
        text = _process_content(content)
        return text + "\n" if text else ""
    
    elif node_type == "bulletList":
        return _process_list(content, bullet=True)
    
    elif node_type == "orderedList":
        return _process_list(content, bullet=False)
    
    elif node_type == "listItem":
        text = _process_content(content)
        # Strip trailing newline from list item content
        return text.rstrip("\n")
    
    elif node_type == "hardBreak":
        return "\n"
    
    elif node_type == "codeBlock":
        text = _process_content(content)
        return text + "\n" if text else ""
    
    elif node_type == "blockquote":
        text = _process_content(content)
        return text
    
    elif node_type == "rule":
        return "\n"
    
    elif node_type == "inlineCard":
        # Inline cards (links) - extract URL or title
        attrs = node.get("attrs", {})
        return attrs.get("url", "")
    
    elif node_type == "mention":
        # User mentions
        attrs = node.get("attrs", {})
        return f"@{attrs.get('text', attrs.get('id', ''))}"
    
    elif node_type == "emoji":
        attrs = node.get("attrs", {})
        return attrs.get("shortName", "")
    
    elif node_type == "mediaGroup" or node_type == "mediaSingle":
        # Media attachments - skip or add placeholder
        return "[attachment]\n"
    
    elif node_type == "table":
        return _process_table(content)
    
    elif node_type == "tableRow":
        cells = []
        for cell in content:
            cell_text = _extract_node_text(cell).strip()
            cells.append(cell_text)
        return " | ".join(cells) + "\n"
    
    elif node_type == "tableHeader" or node_type == "tableCell":
        return _process_content(content).strip()
    
    else:
        # Unknown node type - try to process content if present
        if content:
            return _process_content(content)
        return ""


def _process_content(content: list) -> str:
    """Process a list of content nodes."""
    if not content:
        return ""
    
    parts = []
    for item in content:
        if isinstance(item, dict):
            text = _extract_node_text(item)
            if text:
                parts.append(text)
    
    return "".join(parts)


def _process_list(items: list, bullet: bool = True) -> str:
    """Process a bullet or ordered list."""
    if not items:
        return ""
    
    lines = []
    for i, item in enumerate(items):
        if isinstance(item, dict):
            prefix = "• " if bullet else f"{i + 1}. "
            item_text = _extract_node_text(item)
            if item_text:
                lines.append(f"{prefix}{item_text}")
    
    return "\n".join(lines) + "\n" if lines else ""


def _process_table(rows: list) -> str:
    """Process a table node."""
    if not rows:
        return ""
    
    lines = []
    for row in rows:
        if isinstance(row, dict):
            row_text = _extract_node_text(row)
            if row_text:
                lines.append(row_text.rstrip("\n"))
    
    return "\n".join(lines) + "\n" if lines else ""
