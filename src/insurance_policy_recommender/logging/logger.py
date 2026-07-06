import logging
import os
from logging.handlers import TimedRotatingFileHandler

ENV = os.getenv("ENV", "dev")
LOG_LEVEL = logging.DEBUG if ENV == "dev" else logging.INFO

logs_path = os.path.join(os.getcwd(), "logs")
os.makedirs(logs_path, exist_ok=True)

LOG_FILE_PATH = os.path.join(logs_path, "app.log")

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s | %(filename)s:%(lineno)d | %(message)s"
)

file_handler = TimedRotatingFileHandler(
    LOG_FILE_PATH,
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)

logging.basicConfig(
    handlers=[file_handler],
    level=LOG_LEVEL,
    format=LOG_FORMAT,
)

logger = logging.getLogger("src.insurance_policy_recommender")