import importlib
import pytest
import os
from typing import Dict
import typer
from typer.testing import CliRunner

jw = importlib.import_module('init-odkx-sync-endpoint')

env = {"HTTPS_DOMAIN":"odk-x.com", "HTTPS_ADMIN_EMAIL":"jesse@odk-x.com"}

runner = CliRunner()

app = typer.Typer()

def test_run_cache_setup(mocker):
    """Test creation of cache file with provided inputs
    """

    mocker.patch('init-odkx-sync-endpoint.is_enforce_https', return_value=True)
    # Mock certificate setup during test as a no-op since it's expensive
    mocker.patch('init-odkx-sync-endpoint.setup_certbot_certificate', return_value=None)
    mocker.patch('init-odkx-sync-endpoint.setup_manual_certificate', return_value=None)

    # Setup a typer app with our test function as the only callback. Use a
    # lambda to bind the env variable to the function invocation since typer
    # invoke can only call it with parameters passed via the test command line,
    # but we want to pass an actual python dictionary.
    app.callback(invoke_without_command=True)(lambda : jw.run_cache_setup(env))

    # Invoke the test application
    result = runner.invoke(app, input="odk-x.com\n\n\njesse@odk-x.com\n\n")

    print("Test run standard output:")
    print(result.stdout)

    # Validate script outputs
    assert "Please provide an admin email for security updates with HTTPS registration" in result.stdout
    assert "If you have not done this yet, please do it now..." in result.stdout

    # Validate the progress file itself
    saved_progress: Dict[str, str] = {}
    try:
        saved_progress = jw.load_progress()
    except OSError:
         pytest.fail("No progress file found")

    saved_env: Dict[str, str] = saved_progress["env"]

    assert saved_env["HTTPS_DOMAIN"] == env["HTTPS_DOMAIN"]
    assert saved_env["HTTPS_ADMIN_EMAIL"] == env["HTTPS_ADMIN_EMAIL"]

def test_check_valid_email():
    # with invalid email address
    app.callback(invoke_without_command=True)(lambda : jw.check_valid_email("invalid-email-odk-x"))
    result = runner.invoke(app, input="valid-domain.com\n\n\ninvalid-email-odk-x\n\n")
    print("Test run standard output:")
    print(result.stdout)

    # Validate script outputs
    assert "Invalid email address: invalid-email-odk-x" in result.stdout
    assert "Re-run this script with the correct email address." in result.stdout

def test_check_valid_domain():
    app.callback(invoke_without_command=True)(lambda : jw.check_valid_domain("invalid-domain"))
    result = runner.invoke(app, input="invalid-domain\n\n\nvalid-email@odk-x.com\n\n")
    print("Test run standard output:")
    print(result.stdout)

    # Validate script outputs
    assert "Invalid domain: invalid-domain" in result.stdout
    assert "Re-run this script with the correct domain." in result.stdout
    
