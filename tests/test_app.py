"""Smoke test: every Streamlit page renders without an exception."""
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from awake.paths import ROOT  # noqa: E402

PAGES = ["Project Overview", "Past Events", "Demand", "Planner", "Assumptions & Data Notes"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, [e.value for e in at.exception]


def test_planner_defaults_reproduce_python_module():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    at.sidebar.radio[0].set_value("Planner").run()
    prod = [m for m in at.metric if m.label == "Production under chosen buffer"][0]
    assert prod.value == "115 items"       # ceil(104 * 1.10)
    at.slider[0].set_value(0).run()        # zero buffer
    prod = [m for m in at.metric if m.label == "Production under chosen buffer"][0]
    assert prod.value == "104 items"
    assert not at.exception
