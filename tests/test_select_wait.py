from backend.app.engine.select_wait import wait_for_valid_select_options


class FakeOption:
    def __init__(self, value="", text=""):
        self.value = value
        self.text = text

    def get_attribute(self, name):
        return self.value if name == "value" else ""

    def inner_text(self):
        return self.text


class FakeOptions:
    def __init__(self, select):
        self.select = select

    def all(self):
        self.select.calls += 1
        return self.select.snapshots[min(self.select.calls - 1, len(self.select.snapshots) - 1)]


class FakeSelect:
    def __init__(self, snapshots):
        self.snapshots = snapshots
        self.calls = 0

    def wait_for(self, **_kwargs):
        return None

    def locator(self, selector):
        assert selector == "option"
        return FakeOptions(self)

    def get_attribute(self, name):
        return "" if name == "title" else ""


def test_wait_for_valid_select_options_waits_until_matching_option():
    select = FakeSelect([
        [FakeOption("", "Carregando dados ...")],
        [FakeOption("1", "SALVADOR")],
        [FakeOption("2", "FORTALEZA")],
    ])

    opts, texts, not_found = wait_for_valid_select_options(
        select,
        option_matches=lambda opt: "fortaleza" in opt.inner_text().lower(),
        timeout=0.2,
        interval=0.001,
    )

    assert not not_found
    assert [opt.get_attribute("value") for opt in opts] == ["2"]
    assert texts == ["FORTALEZA"]
