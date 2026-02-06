import asyncio
import sys
from pathlib import Path
from google import genai

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))
from app.core.config import settings

async def test_model(client, model_name):
    print(f"Testing {model_name}...")
    try:
        # Try new SDK syntax first
        result = await client.aio.models.embed_content(
            model=model_name,
            contents="Hello world"
        )
        print(f"✅ Success with {model_name}!")
        return True
    except Exception as e:
        print(f"❌ Failed with {model_name}: {e}")
        return False

async def main():
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    
    models_to_test = [
        "models/text-embedding-004",
        "models/embedding-001",
        "text-embedding-004",
        "embedding-001"
    ]
    
    for m in models_to_test:
        if await test_model(client, m):
            break

if __name__ == "__main__":
    asyncio.run(main())
