import importlib
import pytest
import os
from typing import Dict
import typer
from typer.testing import CliRunner

jw = importlib.import_module('init-odkx-sync-endpoint')

env = {"HTTPS_DOMAIN":"odk-x.com", "HTTPS_ADMIN_EMAIL":"jesse@odk-x.com"}

runner = CliRunner()

def test_run_cache_setup(mocker):
    """Test creation of cache file with provided inputs
    """
    
    mocker.patch('init-odkx-sync-endpoint.is_enforce_https', return_value=True)
    # Mock certificate setup during test as a no-op since it's expensive
    mocker.patch('init-odkx-sync-endpoint.setup_certbot_certificate', return_value=None)
    mocker.patch('init-odkx-sync-endpoint.setup_manual_certificate', return_value=None)

    jw.setup_translator('en')
    
    # Setup a typer app with our test function as the only callback. Use a
    # lambda to bind the env variable to the function invocation since typer
    # invoke can only call it with parameters passed via the test command line,
    # but we want to pass an actual python dictionary.
    app = typer.Typer()
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

def test_support_for_french(mocker):
    mocker.patch('init-odkx-sync-endpoint.is_enforce_https', return_value=True)
    # Mock certificate setup during test as a no-op since it's expensive
    mocker.patch('init-odkx-sync-endpoint.setup_certbot_certificate', return_value=None)
    mocker.patch('init-odkx-sync-endpoint.setup_manual_certificate', return_value=None)

    jw.setup_translator('fr')

    app = typer.Typer()
    app.callback(invoke_without_command=True)(lambda : jw.run_cache_setup(env))

    # Invoke the test application
    result = runner.invoke(app, input="odk-x.com\n\n\njesse@odk-x.com\n\n")

    print("Test run standard output:")
    print(result.stdout)

    # script outputs should be in french
    assert "Veuillez fournir un e-mail d'administrateur pour les mises à jour de sécurité avec l'enregistrement HTTPS" in result.stdout
    assert "Si vous ne l'avez pas encore fait, faites-le maintenant..." in result.stdout
