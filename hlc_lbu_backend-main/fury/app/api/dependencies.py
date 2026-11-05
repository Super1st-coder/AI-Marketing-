"""FastAPI dependencies"""
from typing import Generator
from utils.strapi_client import StrapiClient
from utils.qdrant_client import QdrantClientWrapper
from utils.postgres_client import PostgresClientWrapper
from utils.langfuse_client import LangfuseClientWrapper


def get_strapi_client() -> Generator[StrapiClient, None, None]:
    """Get Strapi client"""
    client = StrapiClient()
    try:
        yield client
    finally:
        pass


def get_qdrant_client() -> Generator[QdrantClientWrapper, None, None]:
    """Get Qdrant client"""
    client = QdrantClientWrapper()
    try:
        yield client
    finally:
        pass


def get_postgres_client() -> Generator[PostgresClientWrapper, None, None]:
    """Get PostgreSQL client"""
    client = PostgresClientWrapper()
    try:
        yield client
    finally:
        pass


def get_langfuse_client() -> Generator[LangfuseClientWrapper, None, None]:
    """Get Langfuse client"""
    client = LangfuseClientWrapper()
    try:
        yield client
    finally:
        pass

