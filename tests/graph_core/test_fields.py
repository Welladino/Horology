"""Document fields copied from the Document Index keep one stored form."""
import pytest

from graph_core.documents import fields


@pytest.mark.parametrize("value,expected", [("Welladino", "welladino"), ("welladino", "welladino"),
                                            ("Article Aggregator", "article-aggregator"), ("  E-commerce ", "e-commerce"),
                                            ("", None), (None, None)])
def test_domain_normal_form(value, expected):
    assert fields.domain(value) == expected


@pytest.mark.parametrize("value,expected", [(12, "12"), (12.0, "12"), (" 007 ", "7"), ("", None), (None, None)])
def test_pipeline_id(value, expected):
    assert fields.pipeline_id(value) == expected


@pytest.mark.parametrize("value", ["PL-7", "1.5", "twelve"])
def test_pipeline_id_rejects_non_numbers(value):
    with pytest.raises(ValueError):
        fields.pipeline_id(value)
