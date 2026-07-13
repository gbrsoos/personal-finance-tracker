import logging
import subprocess
import time
import tomllib

import requests

from config import settings

logging.basicConfig(level=logging.ERROR)

logger = logging.getLogger(__name__)


def get_latest_release():
    """
    Query the GitHub API and return the tag name of the latest release of
    the personal-finance-tracker repository.
    """
    payload = requests.get("https://api.github.com/repos/gbrsoos/personal-finance-tracker/releases/latest")
    latest_tag = payload.json()["tag_name"]

    return latest_tag


def get_deployed_version():
    """
    Read the project version currently deployed from pyproject.toml.
    """
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
        return data.get("project", {}).get("version")


def deploy():
    """
    Pull the latest changes, reinstall dependencies, run pending Alembic
    migrations, and restart the scheduler and dashboard services.
    """
    subprocess.run(["git", "pull"], cwd=settings.deploy_cwd, check=True)
    subprocess.run(["venv/bin/pip", "install", "poetry"], cwd=settings.deploy_cwd, check=True)
    subprocess.run(["poetry", "install"], cwd=settings.deploy_cwd, check=True)
    subprocess.run(["venv/bin/alembic", "upgrade", "head"], cwd=settings.deploy_cwd, check=True, env={"PYTHONPATH": "src"})
    subprocess.run(["venv/bin/python", "src/scheduler.py"], cwd=settings.deploy_cwd, check=True, env={"PYTHONPATH": "src"})
    subprocess.run(["sudo", "systemctl", "restart", "finance-dashboard"], check=True)


def main():
    """
    Poll the latest GitHub release every 10 minutes and trigger a deploy
    whenever it differs from the currently deployed version.
    """
    while True:
        try:
            if f"v{get_deployed_version()}" != get_latest_release():
                deploy()
        except Exception as e:
            logger.error("Deploy watcher error: %s", e)
        time.sleep(600)


if __name__ == "__main__":
    main()