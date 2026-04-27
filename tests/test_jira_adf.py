"""Tests for Jira ADF (Atlassian Document Format) extraction."""

import pytest
from src.jira_adf import extract_text_from_adf


class TestExtractTextFromADF:
    """Tests for extract_text_from_adf function."""

    def test_none_input_returns_empty_string(self):
        """None input should return empty string."""
        assert extract_text_from_adf(None) == ""

    def test_empty_string_returns_empty_string(self):
        """Empty string should return empty string."""
        assert extract_text_from_adf("") == ""
        assert extract_text_from_adf("   ") == ""

    def test_plain_string_returned_as_is(self):
        """Plain text string should be returned unchanged."""
        text = "This is a plain text description"
        assert extract_text_from_adf(text) == text

    def test_simple_doc_with_paragraph(self):
        """Simple document with one paragraph."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Hello world"}
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Hello world" in result

    def test_multiple_paragraphs(self):
        """Document with multiple paragraphs."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "First paragraph"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Second paragraph"}]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "First paragraph" in result
        assert "Second paragraph" in result

    def test_bullet_list(self):
        """Document with bullet list."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item one"}]
                                }
                            ]
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Item two"}]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Item one" in result
        assert "Item two" in result
        assert "•" in result  # Bullet character

    def test_ordered_list(self):
        """Document with ordered list."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "orderedList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "First step"}]
                                }
                            ]
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Second step"}]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "First step" in result
        assert "Second step" in result
        assert "1." in result
        assert "2." in result

    def test_heading(self):
        """Document with heading."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": "Main Heading"}]
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Body text"}]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Main Heading" in result
        assert "Body text" in result

    def test_hard_break(self):
        """Document with hard break."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Line one"},
                        {"type": "hardBreak"},
                        {"type": "text", "text": "Line two"}
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Line one" in result
        assert "Line two" in result

    def test_json_string_input(self):
        """JSON string should be parsed and processed."""
        adf_json = '{"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "From JSON"}]}]}'
        result = extract_text_from_adf(adf_json)
        assert "From JSON" in result

    def test_invalid_json_string_returned_as_is(self):
        """Invalid JSON that doesn't parse should be returned as plain text."""
        text = "This looks like {json but isn't valid"
        result = extract_text_from_adf(text)
        assert result == text

    def test_empty_doc(self):
        """Empty document should return empty string."""
        adf = {"type": "doc", "version": 1, "content": []}
        assert extract_text_from_adf(adf) == ""

    def test_unsupported_node_type_ignored(self):
        """Unsupported node types should be safely ignored."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Before"}]
                },
                {
                    "type": "unknownNodeType",
                    "content": []
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "After"}]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Before" in result
        assert "After" in result

    def test_nested_formatting(self):
        """Text with nested formatting marks."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Normal "},
                        {"type": "text", "text": "bold", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": " text"}
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Normal bold text" in result

    def test_code_block(self):
        """Document with code block."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "codeBlock",
                    "attrs": {"language": "python"},
                    "content": [{"type": "text", "text": "print('hello')"}]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "print('hello')" in result

    def test_mention(self):
        """Document with user mention."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Assigned to "},
                        {"type": "mention", "attrs": {"id": "123", "text": "John Doe"}}
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Assigned to" in result
        assert "@John Doe" in result

    def test_real_jira_adf_example(self):
        """Test with a realistic Jira ADF document."""
        adf = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "User Story"}]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "As a "},
                        {"type": "text", "text": "user", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": ", I want to login so I can access my account."}
                    ]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": "Acceptance Criteria"}]
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "User can enter email and password"}]
                                }
                            ]
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Invalid credentials show error message"}]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        
        assert "User Story" in result
        assert "user" in result
        assert "login" in result
        assert "Acceptance Criteria" in result
        assert "email and password" in result
        assert "error message" in result

    def test_table(self):
        """Document with table."""
        adf = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableHeader",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "Name"}]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableHeader",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "Value"}]
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "Item 1"}]
                                        }
                                    ]
                                },
                                {
                                    "type": "tableCell",
                                    "content": [
                                        {
                                            "type": "paragraph",
                                            "content": [{"type": "text", "text": "100"}]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        result = extract_text_from_adf(adf)
        assert "Name" in result
        assert "Value" in result
        assert "Item 1" in result
        assert "100" in result
