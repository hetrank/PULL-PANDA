import importlib
import sys
import builtins
import pytest


# -----------------------------------------------------------
# Helper to reload module with a clean environment
# -----------------------------------------------------------
def reload_config_with_env(env_vars):
    """
    Reload config.py after setting new environment variables.
    """
    # Patch os.getenv globally inside the module
    with pytest.MonkeyPatch().context() as mp:
        for key, value in env_vars.items():
            mp.setenv(key, value)

        # Make sure dotenv load does nothing
        mp.setenv("PYTHON_DOTENV_DISABLED", "1")

        # Remove cached module so import executes again
        if "config" in sys.modules:
            del sys.modules["config"]

        # Now import with modified env
        import config
        return config


# -----------------------------------------------------------
# TESTS
# -----------------------------------------------------------

def test_config_successful_load_full_env():
    """
    All required environment variables present → no SystemExit.
    """
    cfg = reload_config_with_env({
        "OWNER": "test_owner",
        "REPO": "test_repo",
        "GITHUB_TOKEN": "tok123",
        "GROQ_API_KEY": "groq-key",
        "PINECONE_API_KEY": "pine-key",
        "PINECONE_INDEX_NAME": "pine-index",
        "PR_NUMBER": "42"
    })

    assert cfg.OWNER == "test_owner"
    assert cfg.REPO == "test_repo"
    assert cfg.GITHUB_TOKEN == "tok123"
    assert cfg.GROQ_API_KEY == "groq-key"
    assert cfg.PINECONE_API_KEY == "pine-key"
    assert cfg.PINECONE_INDEX_NAME == "pine-index"
    assert cfg.PR_NUMBER == 42


def test_config_missing_env_raises_system_exit():
    """
    If any required variable missing → SystemExit with correct message.
    """
    missing_env = {
        "OWNER": "",
        "REPO": "",
        "GITHUB_TOKEN": "",
        "GROQ_API_KEY": "",
        "PINECONE_API_KEY": "",
        "PINECONE_INDEX_NAME": "",
    }

    with pytest.raises(SystemExit) as e:
        reload_config_with_env(missing_env)

    msg = str(e.value)
    assert "Missing required .env variables" in msg
    assert "OWNER" in msg
    assert "REPO" in msg
    assert "GITHUB_TOKEN" in msg
    assert "GROQ_API_KEY" in msg
    assert "PINECONE_API_KEY" in msg
    assert "PINECONE_INDEX_NAME" in msg


def test_config_invalid_pr_number_defaults_to_zero():
    """
    Invalid PR_NUMBER → fallback to 0.
    """
    cfg = reload_config_with_env({
        "OWNER": "ok",
        "REPO": "ok",
        "GITHUB_TOKEN": "ok",
        "GROQ_API_KEY": "ok",
        "PINECONE_API_KEY": "ok",
        "PINECONE_INDEX_NAME": "ok",
        "PR_NUMBER": "abc"   # invalid integer
    })

    assert cfg.PR_NUMBER == 0


def test_config_pr_number_not_set_defaults_to_zero():
    """
    Missing PR_NUMBER → default to 0.
    """
    cfg = reload_config_with_env({
        "OWNER": "ok",
        "REPO": "ok",
        "GITHUB_TOKEN": "ok",
        "GROQ_API_KEY": "ok",
        "PINECONE_API_KEY": "ok",
        "PINECONE_INDEX_NAME": "ok",
    })

    assert cfg.PR_NUMBER == 0


def test_config_pr_number_negative_logs_warning(capsys):
    """
    PR_NUMBER <= 0 prints a warning.
    """
    cfg = reload_config_with_env({
        "OWNER": "ok",
        "REPO": "ok",
        "GITHUB_TOKEN": "ok",
        "GROQ_API_KEY": "ok",
        "PINECONE_API_KEY": "ok",
        "PINECONE_INDEX_NAME": "ok",
        "PR_NUMBER": "-5"
    })

    assert cfg.PR_NUMBER == -5  # parsed directly
    out = capsys.readouterr().out
    assert "WARNING: PR_NUMBER is missing or invalid" in out

@pytest.mark.parametrize("varname", [
    "OWNER",
    "REPO",
    "GITHUB_TOKEN",
    "GROQ_API_KEY",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
])

def test_config_each_variable_missing_individually(varname):
    """
    Each individual missing variable must trigger SystemExit,
    hitting all True-branches of the individual if-blocks.
    """
    # All valid by default
    base_env = {
        "OWNER": "ok",
        "REPO": "ok",
        "GITHUB_TOKEN": "ok",
        "GROQ_API_KEY": "ok",
        "PINECONE_API_KEY": "ok",
        "PINECONE_INDEX_NAME": "ok",
        "PR_NUMBER": "10",
    }

    # Set the one variable to be missing
    base_env[varname] = ""

    with pytest.raises(SystemExit) as e:
        reload_config_with_env(base_env)

    msg = str(e.value)
    assert varname in msg
