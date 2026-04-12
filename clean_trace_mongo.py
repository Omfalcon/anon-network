"""
Delete the `fragments` collection contents (Phase 5 ME attestations).
Use after regenerating keys with generate_keyring.py or if trace verification fails.

Usage (repo root, PYTHONPATH=.):
  python clean_trace_mongo.py
"""
import sys

from pymongo import MongoClient

from config import DB_NAME, MONGO_URI


def main():
    client = MongoClient(MONGO_URI)
    n = client[DB_NAME]["fragments"].delete_many({}).deleted_count
    print(f"Deleted {n} document(s) from fragments collection.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
