"""Tests for FHIRPath expression helpers."""

from __future__ import annotations

from sdc.fhirpath import (
    answer_value,
    coding,
    ctx_where,
    item_path,
    nested_answer_value,
    placeholder,
    res_context,
    res_where,
)


class TestFhirpathHelpers:
    def test_coding(self) -> None:
        result = coding("http://snomed.info/sct", "123")
        assert result == "%factory.Coding('http://snomed.info/sct', '123')"

    def test_item_path(self) -> None:
        result = item_path("q1")
        assert result == "item.where(linkId='q1')"

    def test_answer_value_with_prop(self) -> None:
        result = answer_value("q1", "coding")
        assert result == "item.where(linkId='q1').answer.value.coding"

    def test_answer_value_without_prop(self) -> None:
        result = answer_value("q1")
        assert result == "item.where(linkId='q1').answer.value"

    def test_nested_answer_value(self) -> None:
        result = nested_answer_value("parent", "child", "display")
        assert result == (
            "item.where(linkId='parent').answer.item"
            ".where(linkId='child').answer.value.display"
        )

    def test_nested_answer_value_without_prop(self) -> None:
        result = nested_answer_value("parent", "child")
        assert result == (
            "item.where(linkId='parent').answer.item"
            ".where(linkId='child').answer.value"
        )

    def test_placeholder(self) -> None:
        expr = answer_value("q1")
        result = placeholder(expr)
        assert result == "{{item.where(linkId='q1').answer.value}}"

    def test_ctx_where(self) -> None:
        result = ctx_where("code='123'")
        assert result == "%context.where(code='123')"

    def test_res_context(self) -> None:
        result = res_context("item.where(linkId='q1')")
        assert result == "%resource.item.where(linkId='q1')"

    def test_res_where(self) -> None:
        result = res_where("type='Observation'")
        assert result == "%resource.where(type='Observation')"
