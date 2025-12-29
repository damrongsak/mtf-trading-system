# **Project MTF: The Trading Operating System Specification**

**Vision:** พัฒนาโครงสร้างพื้นฐาน (OS) สำหรับระบบการตัดสินใจเทรดแบบ Multi-Agent ที่แยกความจริงของตลาด ความเสี่ยง และ AI ออกจากกันอย่างเด็ดขาด โดยมีกลยุทธ์เป็นเพียง Plugin ที่ถอดเปลี่ยนได้ เพื่อความโปร่งใสและการขยายผลที่ยั่งยืน

## **1\. The Core Philosophy (The MTF Way)**

* **Decoupling Reality from Decision:** ระบบแยก "Data Engine" (Layers 1-3) ออกจาก "Decision Logic" (Strategy Plugin)  
* **Risk as Kernel:** ชั้นความเสี่ยง (Layer 4\) คือ Kernel ที่มีอำนาจสูงสุด สามารถ Override ทุกคำสั่งเพื่อความปลอดภัยของเงินทุน  
* **AI as Intelligence Advisor:** AI (Layer 5\) ทำหน้าที่เป็น Reasoning Agent ที่ประมวลผลบริบท (Context) เพื่อให้คำแนะนำ แต่ไม่มีสิทธิ์สั่ง Execution โดยตรง  
* **Stateless & Deterministic:** กลยุทธ์ต้องเป็น Deterministic Policy ที่อ่าน MarketState แล้วตัดสินใจทันที เพื่อให้สามารถทำ Audit และ Replay ได้ 100%

## **2\. Multi-Agent Decision Framework (The 5-Layer Core)**

แม้ระบบจะทำงานแบบ Agentic แต่สถาปัตยกรรมยังคงยึดโยงกับ 5 Layers หลักเพื่อความแม่นยำทางเทคนิค:

### **Layer 1: Probability Agent (The Boundary)**

* **หน้าที่:** คำนวณขอบเขตความเป็นไปได้ทางสถิติ (Price Discovery)  
* **Key Tech:** Monte Carlo Simulations, Block Bootstrap, Volatility Clustering  
* **Output:** p10 / p50 / p90 Distribution levels

### **Layer 2: Structure Agent (The Edge)**

* **หน้าที่:** นิยามโครงสร้างทางกายภาพและ "แรงดึงดูด" ของตลาด  
* **Key Tech:** ATR-normalized Grid, Grid Index, Open Interest (OI) Density Nodes  
* **Output:** Structural zones และค่าเบี่ยงเบนจากค่าเฉลี่ยทางสถิติ

### **Layer 3: Execution Context Agent (The Filter)**

* **หน้าที่:** ตรวจสอบคุณภาพและจังหวะการเข้าเทรดด้วย Logic ชั้นสูง  
* **Key Tech:** SMC Logic (Liquidity Sweep, CHoCH, Order Block, FVG validation)  
* **Result:** execution\_allowed (Status) และ Quality Score

### **Layer 4: Risk & Guardrail Agent (The Kernel)**

* **หน้าที่:** ระบบควบคุมความปลอดภัยขั้นสูงสุด (Hard Constraints)  
* **Operations:** Dynamic Position Sizing, ATR-based Stops, Exposure Control, Kill Switch  
* **Constraint:** Layer นี้ทำงานอิสระและสามารถปฏิเสธคำสั่งจากทุก Agent หากผิดเงื่อนไขความเสี่ยง

### **Layer 5: Reasoning & Synthesis Agent (The AI Assistant)**

* **หน้าที่:** สังเคราะห์ข้อมูล Unstructured และให้เหตุผลสนับสนุนการตัดสินใจ  
* **Stack:** Multi-agent orchestration \+ **RAG over Structured & Textual Knowledge**  
* **Output:** AgentRecommendation {Action, Confidence, Rationale}

## **3\. RAG: Context Retrieval Engine**

ในระบบ MTF RAG ไม่ใช่แค่การค้นหาเอกสาร แต่คือการดึงบริบท (Context) มาสนับสนุนการตัดสินใจ:

* **Retrieve:** ดึงข้อมูลจาก Historical Trades, Similar Market Regimes, และ Strategy Playbooks  
* **Augment:** นำข้อมูลจาก Layer 1-3 มาทำ Prompt Engineering เพื่อสร้าง Market Hypothesis  
* **Generate:** สร้าง Trade Rationale และ Risk Explanation ที่มนุษย์สามารถตรวจสอบได้

## **4\. Evaluation & Monitoring (The Gold Standard)**

ระบบถูกออกแบบให้มีการวัดผลที่เข้มข้น (Evaluation Pipeline) เพื่อให้มั่นใจว่าเป็น Production-grade:

### **4.1 Multi-Level Evaluation**

* **Offline Eval:** Backtest metrics (Sharpe Ratio, Max Drawdown, Win Rate)  
* **Online Eval:** การเปรียบเทียบผลลัพธ์ระหว่าง Live Trading และ Paper Trading ในสภาพแวดล้อมจริง  
* **LLM Eval:** ตรวจสอบ Decision Consistency และ Hallucination Rate (ตรวจสอบว่า AI ให้เหตุผลที่ขัดกับข้อมูลดิบหรือไม่)

### **4.2 Decision Traceability & Logging**

ทุกการตัดสินใจจะถูกบันทึกอย่างละเอียด (Audit Trail):

* **Prompt & Context Versioning:** บันทึกว่า AI เห็นอะไรในขณะนั้น  
* **Tool Call History:** บันทึกการเรียกใช้ข้อมูลจาก Layer อื่น ๆ  
* **Outcome Feedback Loop:** บันทึกผลลัพธ์เพื่อใช้เป็น Dataset ในการพัฒนา Agent ในอนาคต

## **5\. Strategy Plugin Interface (The Contract)**

กลยุทธ์ (Strategy) ทำหน้าที่เป็น Policy ที่อ่านสรุปจากทุก Agent:

### **5.1 Input: MarketState (Single Source of Truth)**

{  
  "market\_state": {  
    "probability": { "p10": 2600, "p50": 2650, "p90": 2700 },  
    "structure": { "grid\_index": \-2, "oi\_node\_proximity": 0.85 },  
    "execution": { "is\_ob\_active": true, "execution\_quality": "A" },  
    "risk\_guardrail": { "max\_allowed\_size": 0.05, "drawdown\_limit\_ok": true }  
  },  
  "agent\_advice": { "bias": "LONG", "confidence": 0.8, "rationale": "Aligning with p10 support and historical high-OI regime" }  
}

## **6\. Definition of Done (DoD) สำหรับระบบ OS**

* \[ \] ทุก Module (Layer 1-5) แยกจากกันชัดเจนและสื่อสารผ่าน API/Schemas  
* \[ \] Strategy Plugin เป็น Stateless และทำงานแบบ Deterministic  
* \[ \] RAG สามารถดึงบริบทที่ถูกต้องตามสภาวะตลาด (Market Regime)  
* \[ \] ระบบ Logging บันทึก Traceability ได้ครบถ้วนสำหรับการทำ Post-mortem Audit  
* \[ \] Risk Agent สามารถบล็อกคำสั่งเทรดได้จริงในทุกกรณีที่ผิดเงื่อนไข