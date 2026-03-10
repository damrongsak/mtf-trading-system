import asyncio
import logging
import sys
import os
from pathlib import Path

# Add parent dir to path to allow importing 'app'
sys.path.append(str(Path(__file__).parent.parent))

from app.tools.cot import COTAnalystTool
from app.tools.oi_drift import OpenInterestDriftTool
from app.tools.open_interest import OpenInterestTool
from app.tools.predictor import PredictorSignalTool
from app.services.gemini import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    print("🚀 Starting Gold Institutional Deep Dive Analysis...")
    
    # 1. Initialize Tools
    cot_tool = COTAnalystTool()
    drift_tool = OpenInterestDriftTool()
    oi_tool = OpenInterestTool()
    predictor_tool = PredictorSignalTool()
    gemini_client = GeminiClient()
    
    # 2. Gather Data
    print("📈 Fetching COT Data...")
    cot_data = await cot_tool.arun({"symbol": "XAUUSD"})
    
    print("📊 Fetching OI Drift Analysis...")
    drift_data = await drift_tool.arun()
    
    print("🎯 Fetching Open Interest Zones...")
    oi_data = await oi_tool.arun({"symbol": "XAUUSD"})
    
    print("🤖 Fetching ML Predictor Signal...")
    predictor_data = await predictor_tool.arun({"symbol": "XAUUSD"})
    
    # 3. Create Synthesis Prompt
    prompt = f"""
    คุณคือนักวิเคราะห์สถาบัน (Institutional Analyst) ของทีม MTF Olympus
    โปรดสรุปข้อมูลเชิงลึก (Deep Dive) ของทองคำ (GOLD/XAUUSD) จากข้อมูลที่รวบรวมได้ด้านล่างนี้:
    
    ---
    ข้อมูล COT (Commitment of Traders):
    {cot_data}
    
    ---
    ข้อมูล Open Interest Drift (Asia vs London):
    {drift_data}
    
    ---
    ข้อมูล Open Interest Zones & Max Pain:
    {oi_data}
    
    ---
    ข้อมูล ML Predictor Signal:
    {predictor_data}
    ---
    
    สิ่งที่ต้องการในรายงาน:
    1. บทวิเคราะห์ทิศทางสถาบัน (Institutional Sentiment)
    2. วิเคราะห์แรงเหวี่ยงของ Open Interest ระหว่างเซสชัน
    3. ความสัมพันธ์กับความเชื่อมั่นของ ML (ML Confidence Correlation)
    4. โซนราคาที่สำคัญและแผนการเทรดแนะนำ
    
    รูปแบบรายงาน: รายละเอียดทางเทคนิคสูง, เป็นมืออาชีพ, ออกแบบสำหรับการอ่านบนมือถือ (Telegram)
    ภาษา: ภาษาไทย (Thai)
    """
    
    print("🔮 Generating Final Technical Report in Thai...")
    try:
        response = await gemini_client.client.aio.models.generate_content(
            model=gemini_client.model_id,
            contents=prompt
        )
        report_thai = response.text
        
        print("\n" + "="*50)
        print("📜 FINAL TECHNICAL REPORT (THAI)")
        print("="*50)
        print(report_thai)
        print("="*50 + "\n")
        
        # Save to file for record
        with open("deep_dive_report_thai.md", "w") as f:
            f.write(report_thai)
            
    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    asyncio.run(main())
