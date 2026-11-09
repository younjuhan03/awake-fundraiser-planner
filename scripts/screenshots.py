"""Save app screenshots to docs/screenshots/ (developer tool; needs `pip install playwright` and Chrome).

    streamlit run app.py --server.port 8765 --server.headless true     # in another terminal
    python scripts/screenshots.py
"""
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
PAGES = {"past_events": "Past Events", "demand": "Demand", "planner": "Planner", "assumptions": "Assumptions & Data Notes"}


def trim(path, pad=40):
    """Crop empty space below the content (the viewport is deliberately tall)."""
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGB")
    main_area = im.crop((320, 0, im.width, im.height))   # skip the sidebar, which spans the full height
    bg = Image.new("RGB", main_area.size, main_area.getpixel((main_area.width - 5, main_area.height - 5)))
    box = ImageChops.difference(main_area, bg).getbbox()
    if box:
        im.crop((0, 0, im.width, min(im.height, box[3] + pad))).save(path)


def main(base="http://localhost:8765"):
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for scheme in ("light", "dark"):
            ctx = browser.new_context(viewport={"width": 1400, "height": 2600}, color_scheme=scheme)
            page = ctx.new_page()
            for name, label in PAGES.items():
                if scheme == "dark" and name not in ("planner",):
                    continue
                page.goto(f"{base}/?page={quote(label)}")
                page.wait_for_selector("h1", timeout=60000)
                page.wait_for_timeout(5000)
                suffix = "" if scheme == "light" else "_dark"
                out = OUT / f"{name}{suffix}.png"
                page.screenshot(path=str(out), full_page=True)
                trim(out)
                print("saved", name + suffix)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
