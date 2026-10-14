"""Section splitting for passage search."""
from graph_core.sections import chunking
from graph_core.sections.service import mean as _mean


def paragraphs(count, size=300, word="alpha"):
    return [" ".join([word] * (size // (len(word) + 1))) + "." for _ in range(count)]


def test_short_and_empty_text():
    assert chunking.split("") == [] and chunking.split("  \n\n ") == []
    assert chunking.split("One line.") == ["One line."]


def test_sections_stay_within_the_limit_and_keep_all_text():
    text = "\n\n".join(paragraphs(40))
    sections = chunking.split(text)
    assert len(sections) > 4 and all(len(s) <= chunking.MAX_CHARS for s in sections)
    assert all(p in "\n\n".join(sections) for p in text.split("\n\n"))


def test_continued_sections_overlap_the_previous_one():
    sections = chunking.split("\n\n".join(paragraphs(20)))
    assert sections[0][-60:] in sections[1]


def test_a_heading_starts_a_clean_section_once_the_current_one_is_full():
    text = "\n\n".join(paragraphs(4) + ["## Pricing"] + paragraphs(2, word="beta"))
    sections = chunking.split(text)
    assert sections[1].startswith("## Pricing") and "alpha" not in sections[1]


def test_an_early_heading_does_not_create_a_tiny_section():
    sections = chunking.split("# Title\n\nShort intro.\n\n## Background\n\nMore text.")
    assert len(sections) == 1


def test_a_huge_paragraph_is_cut_at_sentence_ends():
    text = " ".join(f"Sentence number {i} is here." for i in range(400))
    sections = chunking.split(text)
    assert all(len(s) <= chunking.MAX_CHARS for s in sections)
    assert all(s.endswith(".") for s in sections[:-1])


def test_a_document_over_the_section_limit_is_rejected_whole():
    import asyncio
    import pytest
    from graph_core.sections import service
    long = "\n\n".join(paragraphs(400))
    assert len(chunking.split(long)) > chunking.MAX_SECTIONS  # all sections are returned, none dropped
    with pytest.raises(chunking.TooLong) as raised:
        service.check_length(long)
    assert raised.value.sections == len(chunking.split(long))
    with pytest.raises(chunking.TooLong):  # raised before any embedding call
        asyncio.run(service.embed_document("Long", long))
    service.check_length("\n\n".join(paragraphs(40)))  # within the limit: no error


def test_document_vector_is_the_normalised_mean():
    vector = _mean([[1.0, 0.0], [0.0, 1.0]])
    assert abs(vector[0] - 0.7071) < 1e-3 and abs(sum(x * x for x in vector) - 1) < 1e-9
