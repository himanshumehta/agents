import os


def pytest_collection_finish(session):
    print(f"\nLK_DOTENV_PROBE after collection = {os.environ.get('LK_DOTENV_PROBE')!r}")
