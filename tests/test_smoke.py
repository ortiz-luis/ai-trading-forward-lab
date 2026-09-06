from engine.cli import main
from engine.commands import decide, evaluate, rebuild
from engine.config import Settings, load_settings


def test_default_settings_are_deterministic():
    assert load_settings({}) == Settings(environment="local", starting_capital_eur=1000.0)


def test_settings_can_be_overridden_without_secrets():
    settings = load_settings({
        "AITFL_ENV": "test",
        "AITFL_STARTING_CAPITAL_EUR": "2500",
    })
    assert settings == Settings(environment="test", starting_capital_eur=2500.0)


def test_commands_are_offline_and_ready():
    settings = Settings()
    assert decide(settings)["network_used"] is False
    assert evaluate(settings)["network_used"] is False
    assert rebuild(settings)["network_used"] is False
    assert decide(settings)["status"] == "ready"


def test_cli_commands_return_success(capsys):
    for command in ("decide", "evaluate", "rebuild"):
        assert main([command]) == 0
        output = capsys.readouterr().out
        assert f'"command": "{command}"' in output
