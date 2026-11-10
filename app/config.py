import os
from dotenv import load_dotenv

load_dotenv()

GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
MOCK_GNANI: bool = os.getenv("MOCK_GNANI", "0") == "1"
SHOP_NAME: str = os.getenv("SHOP_NAME", "My Shop")

