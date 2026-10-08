"""Layer 1: every form with a reference INI must generate the same reader behavior.

Differences are allowed only when tests/known_differences.py lists them with a reason. A listed
difference that no longer happens also fails, so the list stays accurate.
"""
import pytest

from helpers import compare_with_reference, fixtures_available, form_names, reference_names

try:
    # Lists real config names, so it is kept out of the public repo like the fixtures
    from known_differences import KNOWN_DIFFERENCES
except ImportError:
    KNOWN_DIFFERENCES = None

pytestmark = pytest.mark.skipif(
    not fixtures_available() or KNOWN_DIFFERENCES is None,
    reason="Needs private test data: tests/fixtures/ (tools/build_test_fixtures.py) and tests/known_differences.py.",
)


def known_for(name):
    known = {}
    for (category, reason), configs in KNOWN_DIFFERENCES.items():
        for key in configs.get(name, []):
            known[tuple(key)] = f"{category}: {reason}"
    return known


def describe(differences):
    return "\n".join(
        f"  [{section}] {key}: generated {generated}, reference {reference}"
        for (section, key), (generated, reference) in sorted(differences.items())
    )


@pytest.mark.parametrize("name", reference_names())
def test_matches_reference(name):
    differences, _ = compare_with_reference(name)
    known = known_for(name)

    unexpected = {key: values for key, values in differences.items() if key not in known}
    assert not unexpected, f"{name} differs from its reference INI:\n{describe(unexpected)}"

    fixed = sorted(key for key in known if key not in differences)
    assert not fixed, f"{name} now matches its reference for {fixed}. Remove them from known_differences.py."


def test_known_differences_name_real_configs():
    names = set(reference_names())
    listed = {name for configs in KNOWN_DIFFERENCES.values() for name in configs}
    assert listed <= names, f"known_differences.py lists configs with no reference INI: {sorted(listed - names)}"


def test_every_reference_has_a_form():
    assert set(reference_names()) <= set(form_names())
