import pytest

from skill_lint.frontmatter import FrontmatterError, parse


def test_parses_plain_and_quoted_values():
    doc = parse('---\nname: my-skill\ndescription: "Does a thing: well"\nlicense: \'MIT\'\n---\n\n# Body\n')
    assert doc.fields == {"name": "my-skill", "description": "Does a thing: well", "license": "MIT"}
    assert doc.field_lines["description"] == 3
    assert doc.body.strip() == "# Body"
    assert doc.body_start == 6


def test_folded_and_literal_block_scalars():
    doc = parse("---\nname: a\ndescription: >\n  First line\n  second line.\nnotes: |\n  one\n  two\n---\nbody")
    assert doc.fields["description"] == "First line second line."
    assert doc.fields["notes"] == "one\ntwo"


def test_plain_value_continued_on_indented_lines():
    doc = parse("---\nname: a\ndescription: Starts here\n  and continues here.\n---\nbody")
    assert doc.fields["description"] == "Starts here and continues here."


def test_nested_mapping_is_kept_as_raw_text():
    doc = parse("---\nname: a\nmetadata:\n  author: someone\n  version: 2\n---\nbody")
    assert "author: someone" in doc.fields["metadata"]


def test_trailing_comment_is_dropped_from_plain_scalar():
    assert parse("---\nname: a  # the id\n---\n").fields["name"] == "a"


@pytest.mark.parametrize(
    "text, message, line",
    [
        ("# No frontmatter\n", "must start with", 1),
        ("---\nname: a\n", "not closed", 1),
        ("---\nname: a\njust some words\n---\n", "expected 'key: value'", 3),
        ("---\nname: a\nname: b\n---\n", "duplicate key", 3),
        ('---\nname: "a\n---\n', "unterminated", 2),
    ],
)
def test_malformed_frontmatter_reports_the_line(text, message, line):
    with pytest.raises(FrontmatterError, match=message) as caught:
        parse(text)
    assert caught.value.line == line
