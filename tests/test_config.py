import importlib


def test_config_reads_environment(monkeypatch):
    from src import config

    with monkeypatch.context() as env:
        env.setenv("APP_NAME", "Test Assistant")
        env.setenv("HOST", "0.0.0.0")
        env.setenv("PORT", "8123")
        env.setenv("NVIDIA_API_KEY", "test-key")
        env.setenv("NVIDIA_MODEL", "test/model")
        env.setenv("NVIDIA_BASE_URL", "https://example.test/v1/")

        importlib.reload(config)

        assert config.APP_NAME == "Test Assistant"
        assert config.HOST == "0.0.0.0"
        assert config.PORT == 8123
        assert config.NVIDIA_API_KEY == "test-key"
        assert config.NVIDIA_MODEL == "test/model"
        assert config.NVIDIA_BASE_URL == "https://example.test/v1"

    importlib.reload(config)
