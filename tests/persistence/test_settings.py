from typing import ClassVar

from game.persistence import settings


class FakeQSettings:
    values: ClassVar[dict[str, object]] = {}

    def __init__(self, organization: str, application: str) -> None:
        self.organization = organization
        self.application = application

    def value(self, key: str, default=None, value_type=None):
        value = self.values.get(key, default)
        return value_type(value) if value_type is not None else value

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value


def test_settings_persist_the_last_implemented_puzzle(monkeypatch):
    FakeQSettings.values = {}
    monkeypatch.setattr(settings, "QSettings", FakeQSettings)

    settings.save_settings(settings.AppSettings(360, "super-looper"))

    assert settings.load_settings() == settings.AppSettings(360, "super-looper")


def test_settings_fall_back_to_looper_when_the_saved_puzzle_is_unavailable(monkeypatch):
    FakeQSettings.values = {"puzzle_id": "hyper-looper"}
    monkeypatch.setattr(settings, "QSettings", FakeQSettings)

    assert settings.load_settings().puzzle_id == "looper"
