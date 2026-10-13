import os

from src.account_deletion import demo


if __name__ == "__main__":
    if "INFRAI_API_KEY" not in os.environ:
        raise SystemExit("Set INFRAI_API_KEY before running the live demo")
    print(demo())
