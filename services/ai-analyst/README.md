# 🧠 AI Analyst Service (ระบบผู้ช่วยวิเคราะห์และให้คำปรึกษาด้วย AI)

## 📌 ภาพรวม (Overview)
**AI Analyst Service** เป็นไมโครเซอร์วิสหัวใจหลักใน MTF Trading System ที่ทำหน้าที่เปรียบเสมือนนักวิเคราะห์และผู้จัดการความเสี่ยงระดับสถาบัน โดยใช้พลังของ **Google Gemini 2.5 (Pro/Flash)** ผสานกับสถาปัตยกรรม **Agentic RAG (Retrieval-Augmented Generation)** ผ่านการทำ Orchestration ด้วย **LangGraph** สำหรับการแจกแจงวิเคราะห์ตลาด, โครงสร้างราคา, จิตวิทยาการเทรด และวางแผนกลยุทธ์.

## 🏗️ สถาปัตยกรรมและการไหลของข้อมูล (Architecture & Dataflow)

### ส่วนประกอบหลัก (System Components)
บริการนี้จัดการเวิร์กโฟลว์ของ AI Agents และ Tools แบบโมดูลาร์:
*   **FastAPI**: เป็น Entry point สำหรับรับ Request และ Routing (`main.py`)
*   **LangGraph Orchestration**: การจัดการ State และ Node ของ Agent (`StrategyAdvisor`, `MarketObserver`, `DailyBriefing`)
*   **Services**: คอร์ลอจิก เช่น `GeminiClient`, `RAGService`, `MemoryService` (Qdrant), และ `SentimentService`
*   **Tools**: เครื่องมือเฉพาะทางสำหรับดึงข้อมูล เช่น SMC, กราฟราคา, ข่าว, และระบบเทรด
*   **Persistence**: ใช้ **Redis** สำหรับหน่วยความจำระยะสั้น (Checkpoints/Semantic Cache) และ **Qdrant** สำหรับระยะยาว (Vector DB)

### ⚡ ฟีเจอร์ที่ปรับแต่งเพื่อประสิทธิภาพสูง (High-Performance Features)
*   **Layer 0 Redis Spot Fetching**: อ่านข้อมูลราคาปัจจุบัน (`features:XAUUSD:M15`) จาก Redis โดยตรง (ความหน่วง < 2ms) เพื่อป้องกัน HTTP Timeouts
*   **Programmatic Tool Deduplication**: สกัดกั้นและลดการเรียก Tools ซ้ำซ้อนของ LLM อัตโนมัติ เพื่อลดโหลดของ Backend Services
*   **Semantic Caching**: จดจำคำตอบและบริบทคำถามที่เหมือนกันจาก Redis ทำให้ตอบกลับได้ทันทีโดยไม่ต้องเรียก LLM ซ้ำ
*   **Parallel Execution**: รันเครื่องมือตรวจสอบตลาด (Market Scan) และสรุปข่าวพร้อมกันในแบบ Asynchronous (`asyncio.gather`)
*   **Context & Token Pruning**: มีกลไก Node `Summarizer` เพื่อย่อขนาด Scratchpad หากข้อมูลดิบยาวเกินไป ป้องกันการชน Context Window Limit (โดยเฉพาะ Flash Lite)

### 🤖 เวิร์กโฟลว์ของเอเจนต์ (Agent Workflows)

#### 1. Strategy Advisor (`StateGraph`)
Flow หลักสำหรับการสนทนา (Chat) ตลอดจนการออกแบบกลยุทธ์ และให้คำแนะนำ:
1.  **Query Optimizer**: ใช้ `Gemini Flash` ปรับแต่งคำถาม และแยกแยะ Intent (เช่น `TOOL_USE`, `MARKET_ANALYSIS`, `RESEARCH`)
2.  **Router**: แยกเส้นทางตาม Intent หากเป็น Tool Use ให้เข้าวงจรค้นหาเครื่องมือทันที
3.  **Retrieval (RAG)**: ค้นหา User Facts (จำได้ว่าผู้ใช้เคยเทรดอะไร), System Docs, และ Code กลยุทธ์ จาก `Qdrant`
4.  **Reasoning**: ใช้ โมเดลแกนหลัก สร้างแผนการวิเคราะห์แบบ Chain of Thought
5.  **Tool Selection**: เลือกเครื่องมือที่ต้องใช้ (พร้อมกลไก Deduplication ทิ้งเครื่องมือที่เลือกมาซ้ำ)
6.  **Execute Tools**: รันเครื่องมือแบบ Async (ควบคู่ไปกับ "Slim mode" หาก Token ใกล้เต็ม)
7.  **Generate**: นำข้อมูลทั้งหมดมาสังเคราะห์เป็นคำตอบหรือแผนการเทรดสุดท้าย
8.  **Memory Write**: บันทึกความจำระยะยาวลง Qdrant และระยะสั้นลง Redis Checkpoint

#### 2. Background Autonomous Observers (เอเจนต์ทำงานเบื้องหลัง)
*   **Stability Observer**: ตรวจสอบสถานะของโมเดล `Predictor` และ `Data Pipeline` ทุกๆ 15 นาที หากระบบล่มจะส่ง **Telegram Alert** ผ่าน `TELEGRAM_CHAT_ID` ทันที
*   **Gold Sentiment Guardian**: อัปเดตข้อมูลข่าวและ Sentiment ของคู่งานแบบ Real-time โดยมีการ Hash-match เพื่อตรวจสอบความเปลี่ยนแปลงก่อนเรียก LLM
*   **Session Drift Monitor**: ประเมินคุณภาพของ Signal เมื่อจบแต่ละ Session เพื่อดูว่ากลยุทธ์เริ่มออกนอกลู่นอกทาง (Drift) หรือไม่

## 🛠️ เครื่องมือระบบที่ AI เรียกใช้ได้ (System Toolset)
AI Analyst สามารถเชื่อมต่อกับ Services อื่นๆ ได้ผ่านเครื่องมือเหล่านี้:
*   **Institutional SMC**: `smc_technical_analysis` (หา Order Blocks, FVGs, เทรนด์ Bias), `liquidity_heatmap`
*   **Market Sentiment & Regime**: `market_state` (ดึง Risk Multiplier จาก Gamma), `cot_analyst`, `open_interest`
*   **Machine Learning**: `get_predictor_forecast`, `get_predictor_signal`
*   **Execution & Risk**: `risk_check` (คำนวณ Lot Size & ความเสี่ยงเทียบกับพอร์ต), `generate_trading_plan`
*   **Macro & Search**: `get_economic_calendar`, `google_search` (ค้นหาข่าวเรียลไทม์)
*   **Comms**: `send_notification` (ส่งอัปเดตแผนและคำเตือนเข้า Telegram)

## 💻 การติดตั้งและใช้งาน (Setup & Installation)

### 1. ความต้องการของระบบ (Prerequisites)
ควรมีตัวจัดการแพ็กเกจ `uv` ที่มีความเร็วสูง:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. ติดตั้ง Dependencies
```bash
cd services/ai-analyst
uv sync
```

### 3. ตัวแปรสภาพแวดล้อม (Environment Variables)
ตั้งค่า `.env` (ที่ Root ของโปรเจกต์):
```bash
# พาร์ท AI
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

# พาร์ท Database & Memory
QDRANT_HOST=qdrant
QDRANT_PORT=6333
REDIS_URL=redis://redis:6379/0

# พาร์ท Notification
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🏃‍♂️ การรันเซอร์วิส (Running the Service)

รันในระบบ Docker (แนะนำ) หรือรันแยกเฉพาะ Backend ได้ด้วย:
```bash
uv run uvicorn app.main:app --reload --port 8000
```
*   **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## 💬 การทดสอบผ่าน CLI (Professional AI Term)
สามารถใช้ CLI เพอร์มินัลที่มีสไตล์สำหรับทดสอบแชตกับ Agentic RAG:

```bash
# ทำงานข้าม Docker Container (เพื่อเลียนแบบ Environment จริง)
docker compose exec ai-analyst python3 scripts/chat_cli.py
```
> **Tip:** ในหน้าต่าง CLI พิมพ์คำว่า `/new` เพื่อล้างความจำและเริ่ม Context ใหม่

## 💡 โครงสร้าง Prompt เพื่อการวิเคราะห์ (Effective Prompting)
เพื่อให้ AI Analyst ทำงานได้อย่างเต็มประสิทธิภาพที่สุด ควรใช้คำสั่งที่ครอบคลุม (High-Fidelity):

**ตัวอย่าง:**
> "Execute Institutional SMC Screening (H1/H4): Map HTF liquidity traps, Order Blocks, and current Phase Displacement. Use market_state to assess CME Gamma Wall context and send the final risk assessment to my Telegram."

## 📂 โครงสร้างโปรเจกต์ (Project Structure)
```text
services/ai-analyst/
├── app/
│   ├── agents/         # LangGraph Nodes & State Definitions (Strategy Advisor)
│   ├── core/           # Prompts แม่แบบ, Pydantic Schemas และ System Configs
│   ├── services/       # GeminiClient, Qdrant/Memory, Sentiment, Observers
│   ├── tools/          # คลาส BaseTool, การเชื่อมต่อ Redis (Layer 0) และ HTTP API (Layer 1)
│   └── main.py         # FastAPI Entry (Endpoints, Middlewares)
├── scripts/            # CLI และสคริปต์ Benchmark สำหรับทดสอบ RAG
├── tests/              # Pytest Suite
├── pyproject.toml      # ไฟล์ Dependencies Setup
└── README.md           # ไฟล์เอกสารนี้ (อัปเดตล่าสุด)
```
