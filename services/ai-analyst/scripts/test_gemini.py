
import asyncio
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

try:
    from app.core.config import settings
    from google import genai
    
    async def main():
        print(f"Checking Gemini Connectivity...")
        if not settings.GOOGLE_API_KEY:
            print("FAIL: API Key missing")
            return

        print(f"API Key: {settings.GOOGLE_API_KEY[:5]}***")
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        print("Client initialized. Sending request to gemini-2.5-flash...")
        
        try:
            # Test simple generation
            res = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents="Ping"
            )
            print(f"Generation Success: {res.text.strip()}")
            
            # Test embedding
            print("Testing Embedding (models/gemini-embedding-001)...")
            res_emb = await client.aio.models.embed_content(
                model="models/gemini-embedding-001",
                contents="Ping"
            )
            print("Embedding Success.")
            if hasattr(res_emb, 'embeddings'):
                print(f"Dimension: {len(res_emb.embeddings[0].values)}")
            
        except Exception as e:
            print(f"Gemini Error: {e}")

    if __name__ == "__main__":
        asyncio.run(main())
except Exception as e:
    print(f"Setup Error: {e}")
