#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import sys


CONFIG_PATH = Path("/app/.daybreak/config.json")
DEFAULTS_PATH = Path("/app/daybreak-defaults")


def env(name: str) -> str:
    return os.getenv(name, "").strip()


def main() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        shutil.copy2(DEFAULTS_PATH / "config.json", CONFIG_PATH)
    agents_path = CONFIG_PATH.parent / "agents"
    if not agents_path.exists():
        shutil.copytree(DEFAULTS_PATH / "agents", agents_path)

    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    system = data.setdefault("system", {})
    bootstrap = system.setdefault("bootstrap_admin", {})
    database = data.setdefault("database", {})

    overrides = {
        "DAYBREAK_ENCRYPT_KEY": (system, "encrypt_key"),
        "DAYBREAK_ADMIN_USERNAME": (bootstrap, "username"),
        "DAYBREAK_ADMIN_EMAIL": (bootstrap, "email"),
        "DAYBREAK_ADMIN_PASSWORD": (bootstrap, "password"),
        "DAYBREAK_DB_PASSWORD": (database, "password"),
    }
    for variable, (section, key) in overrides.items():
        value = env(variable)
        if value:
            section[key] = value

    model_values = {
        "base_url": env("DAYBREAK_MODEL_BASE_URL"),
        "api_key": env("DAYBREAK_MODEL_API_KEY"),
        "model": env("DAYBREAK_MODEL_NAME"),
    }
    for agent in data.get("agents", {}).values():
        for key, value in model_values.items():
            if value:
                agent[key] = value

    temp_path = CONFIG_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    temp_path.replace(CONFIG_PATH)


if __name__ == "__main__":
    main()
    if len(sys.argv) < 2:
        raise SystemExit("missing application command")
    os.execvp(sys.argv[1], sys.argv[1:])
