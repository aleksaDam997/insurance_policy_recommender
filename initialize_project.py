import os
from pathlib import Path

project_name = "insurance_policy_recommender"

list_of_files = [

    # CI/CD
    ".github/workflows/.gitkeep",

    # SOURCE PACKAGE (src layout)
    f"src/{project_name}/__init__.py",

    # Components (ML logic)
    f"src/{project_name}/components/__init__.py",

    # Config manager
    f"src/{project_name}/config/__init__.py",
    f"src/{project_name}/config/configuration.py",

    # logger
    f"src/{project_name}/logging/__init__.py",
    f"src/{project_name}/logging/logger.py",

    # Exceptions
    f"src/{project_name}/exception/__init__.py",
    f"src/{project_name}/exception/exception.py",


    # Constants
    f"src/{project_name}/constants/__init__.py",
    f"src/{project_name}/constants/training_pipeline/__init__.py",

    # Utils
    f"src/{project_name}/utils/__init__.py",
    f"src/{project_name}/utils/utils.py",

    # Pipeline orchestration
    f"src/{project_name}/pipeline/__init__.py",

    # Entity (config + artifacts dataclasses)
    f"src/{project_name}/entity/__init__.py",
    f"src/{project_name}/entity/config_entity.py",
    f"src/{project_name}/entity/artifact_entity.py",

    # ROOT FILES
    "data/.gitkeep",
    "config/config.yaml",
    "params.yaml",
    "schema.yaml",
    "main.py",
    "requirements.txt",
    "notebooks/.gitkeep",
    "setup.py",
    "README.md",
    ".gitignore",
    ".env",

    # Docker
    "Dockerfile",

    # Templates (optional web/UI layer)
    "templates/index.html",
]


for file_path in list_of_files:
    file_path = Path(file_path)

    # If it's a directory (no extension and no special file like Dockerfile/.env)
    if file_path.suffix == "" and file_path.name not in ["Dockerfile", ".env", "main.py", "README.md"]:
        os.makedirs(file_path, exist_ok=True)
        continue

    # Create parent directories
    if file_path.parent:
        os.makedirs(file_path.parent, exist_ok=True)

    # Create file if it doesn't exist
    if not file_path.exists():
        with open(file_path, "w", encoding="utf-8") as f:
            pass
        print(f"Created file: {file_path}")
    else:
        print(f"File already exists: {file_path}")