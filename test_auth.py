import sys
import asyncio
from uuid import uuid4
import json

sys.path.append("/home/bagas/Langchain-API-new")
from mcp_server import check_google_auth

async def main():
    res = await check_google_auth(str(uuid4()), str(uuid4()), ["google_docs_get_document"])
    print("OUTPUT:", res)

if __name__ == "__main__":
    asyncio.run(main())
