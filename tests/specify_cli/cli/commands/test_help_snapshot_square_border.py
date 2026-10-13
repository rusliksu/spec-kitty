"""Square Rich borders must not alter semantic help snapshots."""

import pytest

from tests.specify_cli.cli.commands._help_snapshot import normalize_help

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_square_borders_preserve_option_names_and_descriptions() -> None:
    text = "┌─ Options ─┐\n│ --owned-checkout PATH  Declared checkout. │\n└───────────┘\n"
    assert normalize_help(text) == ["Options", "--owned-checkout PATH Declared checkout."]
