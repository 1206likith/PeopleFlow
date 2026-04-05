from app.core.config import Settings


def test_settings_accept_release_for_debug_flag():
    settings = Settings(_env_file=None, DEBUG="release")

    assert settings.DEBUG is False


def test_settings_accept_dev_for_debug_flag():
    settings = Settings(_env_file=None, DEBUG="dev")

    assert settings.DEBUG is True


def test_settings_accept_release_for_other_boolean_flags():
    settings = Settings(
        _env_file=None,
        DEBUG="release",
        REDIS_ENABLED="release",
        ADMIN_KEY_ENABLED="release",
        ENABLE_METRICS="release",
    )

    assert settings.DEBUG is False
    assert settings.REDIS_ENABLED is False
    assert settings.ADMIN_KEY_ENABLED is False
    assert settings.ENABLE_METRICS is False
