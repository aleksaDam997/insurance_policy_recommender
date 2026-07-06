import pandas as pd
import requests


class APIDataSource():

    def __init__(
        self,
        base_url: str,
        endpoint: str,
        headers: dict | None = None,
        params: dict | None = None,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint.lstrip("/")
        self.headers = headers or {}
        self.params = params or {}
        self.timeout = timeout

    def load(self) -> pd.DataFrame:

        response = requests.get(
            f"{self.base_url}/{self.endpoint}",
            headers=self.headers,
            params=self.params,
            timeout=self.timeout
        )

        response.raise_for_status()

        data = response.json()

        return pd.DataFrame(data)