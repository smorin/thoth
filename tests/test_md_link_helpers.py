"""Tests for Markdown link-safe escaping helpers in thoth.utils.

Covers the security-critical ``md_link_title`` and ``md_link_url`` helpers
that prevent arbitrary search-result content from corrupting ``[title](url)``
syntax or injecting unintended Markdown / HTML into persisted reports.
"""

from __future__ import annotations

from thoth.utils import md_link_title, md_link_url


class TestMdLinkTitle:
    """md_link_title escaping."""

    def test_plain_text_unchanged(self) -> None:
        assert md_link_title("Normal title") == "Normal title"

    def test_escapes_closing_bracket(self) -> None:
        assert md_link_title("A]B") == r"A\]B"

    def test_escapes_opening_bracket(self) -> None:
        assert md_link_title("A[B") == r"A\[B"

    def test_escapes_both_brackets(self) -> None:
        assert md_link_title("[Bracketed] title") == r"\[Bracketed\] title"

    def test_multiple_brackets(self) -> None:
        assert md_link_title("a]b]c[d") == r"a\]b\]c\[d"

    def test_escapes_angle_bracket_html_injection(self) -> None:
        assert md_link_title("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_escapes_closing_angle_bracket(self) -> None:
        assert md_link_title("A > B") == "A &gt; B"

    def test_empty_string(self) -> None:
        assert md_link_title("") == ""

    def test_only_special_chars(self) -> None:
        assert md_link_title("][<>") == r"\]\[&lt;&gt;"

    def test_already_escaped_backslash_not_double_escaped(self) -> None:
        # A literal backslash in the input should pass through unchanged;
        # only [ ] < > characters are touched.
        assert md_link_title("\\[already escaped\\]") == "\\\\[already escaped\\\\]"


class TestMdLinkUrl:
    """md_link_url escaping and scheme validation."""

    def test_https_url_unchanged(self) -> None:
        assert md_link_url("https://example.com/path") == "https://example.com/path"

    def test_http_url_unchanged(self) -> None:
        assert md_link_url("http://example.com/page") == "http://example.com/page"

    def test_closing_paren_encoded(self) -> None:
        assert md_link_url("https://example.com/path(1)") == "https://example.com/path(1%29"

    def test_multiple_closing_parens(self) -> None:
        assert md_link_url("https://example.com/a)b)c") == "https://example.com/a%29b%29c"

    def test_opening_paren_not_encoded(self) -> None:
        # Only closing parens need encoding to protect the link syntax
        result = md_link_url("https://example.com/(test)")
        assert "(" in result
        assert "%29" in result

    def test_javascript_scheme_rejected(self) -> None:
        assert md_link_url("javascript:alert(1)") == ""

    def test_data_scheme_rejected(self) -> None:
        assert md_link_url("data:text/html,<h1>hi</h1>") == ""

    def test_empty_string_rejected(self) -> None:
        assert md_link_url("") == ""

    def test_bare_domain_rejected(self) -> None:
        assert md_link_url("example.com") == ""

    def test_ftp_scheme_rejected(self) -> None:
        assert md_link_url("ftp://example.com/file") == ""

    def test_whitespace_stripped_before_check(self) -> None:
        assert md_link_url("  https://example.com  ") == "https://example.com"

    def test_url_with_fragment(self) -> None:
        url = "https://example.com/page#section"
        assert md_link_url(url) == url

    def test_url_with_query(self) -> None:
        url = "https://example.com/search?q=foo&bar=baz"
        assert md_link_url(url) == url
