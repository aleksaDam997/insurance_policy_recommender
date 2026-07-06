import logging
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv()

DB_HOST=os.getenv("DB_HOST")
DB_USER=os.getenv("DB_USER")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DB_DATABASE=os.getenv("DB_DATABASE")
DB_TABLE=os.getenv("DB_TABLE")
DB_PORT=os.getenv("DB_PORT")

import certifi
certifi.where()

import pandas as pd
import numpy as np
import mysql.connector
from src.insurance_policy_recommender.exception.exception import InsurancePolicyRecommenderException
from src.insurance_policy_recommender.logging.logger import logger

def create_mysql_connection():
    try:

        logger.logging.info("Trying to connect to MySQL database...")
        connection = f'mysql+mysqlconnector://{os.getenv("DB_USER")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_HOST")}:{os.getenv("DB_PORT")}/{os.getenv("DB_DATABASE")}'
        engine = create_engine(connection)
        logger.logging.info("Successfully connected to MySQL database...")
        return engine
    except mysql.connector.Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        raise InsurancePolicyRecommenderException(f"Error connecting to MySQL: {e}")