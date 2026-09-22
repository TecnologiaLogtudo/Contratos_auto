from __future__ import annotations

import time
from typing import Callable


def wait_for_valid_select_options(
    select_locator,
    *,
    dismiss: Callable[[], None] | None = None,
    option_matches: Callable[[object], bool] | None = None,
    timeout: float = 8.0,
    interval: float = 0.25,
) -> tuple[list, list[str], bool]:
    try:
        select_locator.wait_for(state="attached", timeout=6000)
    except Exception:
        pass

    deadline = time.monotonic() + timeout
    options = []
    texts: list[str] = []
    last_valid = []

    while time.monotonic() < deadline:
        if dismiss:
            dismiss()

        options = select_locator.locator("option").all()
        texts = [opt.inner_text().strip() for opt in options]
        title = (select_locator.get_attribute("title") or "").strip().lower()
        valid = [opt for opt in options if (opt.get_attribute("value") or "").strip()]
        last_valid = valid or last_valid

        if valid and (option_matches is None or any(option_matches(opt) for opt in valid)):
            return valid, texts, False
        if any("nenhum registro" in t.lower() for t in texts) or title == "nenhum registro encontrado!":
            return [], texts, True

        time.sleep(interval)

    return last_valid, texts, False
