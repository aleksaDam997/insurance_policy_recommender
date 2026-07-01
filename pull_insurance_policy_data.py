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
from networksecurity.exception.exception import NetworkSecurityException
from networksecurity.logging.logger import logging

class NetworkDataExtract():

    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_DATABASE,
                port=DB_PORT,
                allow_local_infile=True
            )

            cursor = self.conn.cursor()
            cursor.execute("SET GLOBAL local_infile = 1")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS network_data (
                    having_IP_Address INT, URL_Length INT, Shortining_Service INT,
                    having_At_Symbol INT, double_slash_redirecting INT, Prefix_Suffix INT,
                    having_Sub_Domain INT, SSLfinal_State INT, Domain_registeration_length INT,
                    Favicon INT, port INT, HTTPS_token INT, Request_URL INT,
                    URL_of_Anchor INT, Links_in_tags INT, SFH INT, Submitting_to_email INT,
                    Abnormal_URL INT, Redirect INT, on_mouseover INT, RightClick INT,
                    popUpWidnow INT, Iframe INT, age_of_domain INT, DNSRecord INT,
                    web_traffic INT, Page_Rank INT, Google_Index INT,
                    Links_pointing_to_page INT, Statistical_report INT, Result INT
                )
            """)
            cursor.execute("TRUNCATE TABLE network_data")

            self.conn.commit()
            cursor.close()

            self.cursor = self.conn.cursor()
        except Exception as e:
            raise NetworkSecurityException(e, sys)
        
    def csv_to_json_convertor(self, csv_file_path: str) -> None:
        try:
            data = pd.read_csv(csv_file_path)
            data.reset_index(inplace=True, drop=True)
            records = list(json.loads(data.T.to_json()).values())
            return records
        except Exception as e:
            raise NetworkSecurityException(e, sys)
        
    def insert_data_to_mysql_fast(self, records: list, file_path: str) -> None:
        try:

            cursor = self.conn.cursor()

            query = """
            LOAD DATA LOCAL INFILE %s
            INTO TABLE network_data
            FIELDS TERMINATED BY ','
            IGNORE 1 ROWS
            """

            csv_path = file_path.replace("\\", "/")

            cursor.execute(query, (csv_path,))
            self.conn.commit()

            print("CSV uspješno učitan u bazu!")
        except Exception as e:
            raise NetworkSecurityException(e, sys)

    def insert_data_to_mysql_slow(self, records: list) -> None:
        try:

            cursor = self.connection.cursor()

            query = """
                INSERT INTO network_data (
                    having_IP_Address, URL_Length, Shortining_Service, having_At_Symbol,
                    double_slash_redirecting, Prefix_Suffix, having_Sub_Domain, SSLfinal_State,
                    Domain_registeration_length, Favicon, port, HTTPS_token, Request_URL,
                    URL_of_Anchor, Links_in_tags, SFH, Submitting_to_email, Abnormal_URL,
                    Redirect, on_mouseover, RightClick, popUpWidnow, Iframe,
                    age_of_domain, DNSRecord, web_traffic, Page_Rank,
                    Google_Index, Links_pointing_to_page, Statistical_report, Result
                )
                VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                """
            values = [tuple(record.values()) for record in records]

            cursor.executemany(query, values)
            self.connection.commit()

            print("Podaci su uspješno umetnuti u bazu!")
        except Exception as e:
            raise NetworkSecurityException(e, sys)


if __name__ == "__main__":
    try:

        FILE_PATH = "Network_Data\phisingData.csv"

        network_data_extract = NetworkDataExtract()
        records = network_data_extract.csv_to_json_convertor(FILE_PATH)
        network_data_extract.insert_data_to_mysql_fast(records, FILE_PATH)
    except Exception as e:
        raise NetworkSecurityException(e, sys)