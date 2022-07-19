from distutils.command.install import install
import importlib
import pytest
import os
from typing import Dict
import serial
import typer
from typer.testing import CliRunner
jw = importlib.import_module('init-odkx-sync-endpoint')

env = {"HTTPS_DOMAIN":"odk-x", "HTTPS_ADMIN_EMAIL":"jesse@odk-x.com"}

runner = CliRunner()
ser = serial.Serial() 

def test_run_cache_setup(mocker):
    mocker.patch('init-odkx-sync-endpoint.is_enforce_https', return_value=True)
    assert jw.is_enforce_https() == True
    result = runner.invoke(jw.app, input="odk-x\n\n\njesse@odk-x.com\n\n")
    assert "Please provide an admin email for security updates with HTTPS registration" in result.stdout
    assert "If you have not done this yet, please do it now..." in result.stdout 
    saved_env: Dict[str, str] = {}
    try:
        saved_env = jw.parse_env_file(os.path.join(os.path.dirname(__file__), "../config", "https.env"))
    except OSError:
         pytest.fail("No default https configuration file found")

    print(saved_env)
    assert saved_env["HTTPS_DOMAIN"] == env["HTTPS_DOMAIN"]
    assert saved_env["HTTPS_ADMIN_EMAIL"] == env["HTTPS_ADMIN_EMAIL"]
    os._exit(0)
