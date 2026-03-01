import asyncio
import sys
from pathlib import Path

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService
from app.services.gemini import GeminiClient

async def ask_rag(question: str):
    gemini = GeminiClient()
    rag = RAGService(gemini_client=gemini)
    
    print(f"\n[{question}]")
    print("Searching Qdrant...")
    
    try:
        # Search the library
        embedding = await rag._get_embedding(question)
        search_result = rag.qdrant.query_points(
            collection_name="quant_library",
            query=embedding,
            limit=5
        ).points
        
        context = "\n\n".join([hit.payload["content"] for hit in search_result])
        
        prompt = f"""
You are an expert quantitative analyst.
Based on the following context from our quant library, answer the question. Provide citations if possible.
If the answer is not in the context, state that clearly.

Question: {question}

Context:
{context}
"""
        
        print("Asking Gemini...")
        response = await gemini.client.aio.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
        print("Answer:\n", response.text)
        print("-" * 80)
        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    questions = [
        "สูตรการคำนวณ Kelly Criterion สำหรับกรณีที่อัตราการจ่าย (Payout Ratio) ของรายการที่ชนะและแพ้ไม่เท่ากันคืออะไร? และมีคำเตือนอย่างไรในการนำไปใช้จริง? Search the quant library for the answer and provide citations.",
        "เปรียบเทียบความแตกต่างระหว่างกลยุทธ์ Risk Parity และ Mean-Variance Optimization ในการจัดสรรพอร์ตโฟลิโอ? Search the quant library for the answer and provide citations.",
        "อธิบายแนวคิด 'Optimal f' ของ Ralph Vince และมันช่วยแก้ปัญหาเรื่องการบริหารเงิน (Money Management) ที่แตกต่างจาก Kelly อย่างไร? Search the quant library for the answer and provide citations.",
        "หลักการของ 'Order Block' ในมุมมองของหนังสือ RTM (Read The Market) มีความแตกต่างจาก Supply/Demand Zone ทั่วไปอย่างไร? Search the quant library for the answer and provide citations.",
        "ในสภาวะตลาดแบบ 'Liquidity Sweep' เราควรสังเกตพฤติกรรมราคา (Price Action) อย่างไรเพื่อให้ได้จุดเข้าที่ได้เปรียบตามหลัก SMC? Search the quant library for the answer and provide citations.",
        "วิธีการใช้ค่า 'Volatility Multiplier' เพื่อกำหนดระดับ Take Profit และ Stop Loss ตามคำแนะนำในหนังสือ Volatility-based Technical Analysis คืออะไร? Search the quant library for the answer and provide citations.",
        "ขั้นตอนการจัดการกับภาวะ 'Tilt' หรืออารมณ์หลุดในการเทรดตามเทคนิคจากหนังสือ The Mental Game of Trading มีอะไรบ้าง? Search the quant library for the answer and provide citations.",
        "เกณฑ์การวัดคุณภาพของ Alpha ด้วยค่า 'Information Coefficient (IC) > 0.05' ในระบบ MTF Olympus มีที่มาและหลักการคำนวณอย่างไร? Search the quant library for the answer and provide citations.",
        "อธิบายกลไก 'Minimax Regret' ใน Module 3 ของโครงการ และบอกว่าทำไมระบบถึงเลือกใช้วิธีนี้แทนการคำนวณ Risk:Reward แบบปกติ? Search the quant library for the answer and provide citations.",
        "ในคู่มือ Module 4 เรื่อง Execution Edge ระบบมีการจัดการกับสภาวะ 'Institutional Liquidity Depth' อย่างไรเพื่อลด Slippage? Search the quant library for the answer and provide citations."
    ]
    
    for q in questions:
        await ask_rag(q)

if __name__ == "__main__":
    asyncio.run(main())
