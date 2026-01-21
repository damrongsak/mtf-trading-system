# **Project Olympus: Strategy Specification Document**

System Name: Mae Pla Pakka Kiew (MPPK) Algo-Trading System  
Version: 1.0  
Author: AI Assistant (Ref: User Analysis)  
Date: 2026-01-21

## **1\. System Overview (ภาพรวมระบบ)**

ระบบ MPPK ออกแบบมาเพื่อตรวจจับสัญญาณการเทรด (Signal Detection) และบริหารจัดการสถานะ (Trade Management) โดยอิงตามวงจรชีวิตของกราฟ (Graph Life Cycle) เน้นการเทรดใน Timeframe H1 ขึ้นไป โดยใช้ Price Action เป็นตัวกระตุ้น (Trigger) และใช้โครงสร้างราคา (Structure) ในการกำหนดเป้าหมายกำไร

## **2\. Data Structures & Definitions (นิยามข้อมูลและโครงสร้าง)**

### **2.1 Timeframes & Targets (รอบวิ่ง)**

ระบบต้องรองรับ Multi-timeframe โดยมีค่าคงที่สำหรับ "รอบวิ่ง" (TP) ดังนี้:

| Timeframe | Min TP (Points) | Max TP (Points) | Confirmation Candles |
| :---- | :---- | :---- | :---- |
| **H1** | 1,000 | 1,000 | 2 \- 4 |
| **H4** | 1,500 | 3,000 | 1 \- 3 |
| **D1** | 5,000 | 10,000 | 1 \- 3 |
| **W1** | 15,000 | 30,000 | N/A |
| **MN** | 30,000 | Infinite | N/A |

### **2.2 Key Terminology Mapping (ตัวแปรระบบ)**

* **Krob (กรอบ):** ระดับราคาที่เป็น Integer ซึ่งลงท้ายด้วย 0 หรือ 5 (Psychological Levels/Round Numbers).  
  * *Logic:* if (Price % 5 \== 0 || Price % 10 \== 0\) return true;  
* **Sig (ซิก):** Valid Trade Signal (State \= Entry Triggered).  
* **Sai Lang Sig (ไส้หลังซิก):** Reference High/Low สำหรับวาง Stop Loss หรือจุด Invalidation.  
* **Rob (รอบ):** Distance (in Points) จาก Entry ไปยัง TP.

## **3\. Core Logic Modules (โมดูลการทำงานหลัก)**

### **Module A: State Machine (Graph Life Cycle)**

ระบบทำงานเป็น State Machine วนลูปดังนี้:

1. **State: IDLE / SIDEWAYS**  
   * สภาวะ: ไม่มี Active Trade, ราคาวิ่งในกรอบ  
   * Action: Scan หา Signal (Sig) ตามเงื่อนไข Module B  
2. **State: SIGNAL\_DETECTED (Sig)**  
   * สภาวะ: พบ Pattern (PAT1/2/3) และจบแท่งเทียนแล้ว  
   * Action: รอ Confirmation Candles \-\> เข้าสู่ State ACTIVE  
3. **State: ACTIVE\_TRADE**  
   * สภาวะ: เปิด Order แล้ว  
   * Action: Monitor ราคาเทียบกับ Sai Lang Sig (Invalidation) และ Rob (TP)  
   * *Event:* Sig Kam Sig (Re-entry) อาจเกิดขึ้นใน State นี้  
4. **State: REST (พักตัว)**  
   * สภาวะ: ราคาชน TP แล้ว  
   * Action: หยุดเทรดฝั่งเดิม รอราคา Pullback  
     * *H1 Pullback Rule:* 300-500 Points  
     * *H4 Pullback Rule:* 500-1,000 Points  
   * Exit: เมื่อจบระยะพักตัว กลับสู่ State IDLE

### **Module B: Signal Detection (การตรวจจับซิก)**

**เงื่อนไขบังคับ (Pre-condition):**

1. Timeframe ต้อง \>= H1 เท่านั้น  
2. ต้องรอจบแท่งเทียน (Candle Close)

Pattern Logic:  
ระบบต้องตรวจจับ Price Action 3 ประเภท (PAT):

#### **1\. PAT 1 (1 Candle Pattern)**

* **Pi Kha Yang (Buy):** Hammer / Pinbar at Support  
  * Logic: LowerWick \>= 2 \* BodySize AND Close \> Open (Preferred)  
* **Pi Hua Hoy (Sell):** Shooting Star / Pinbar at Resistance  
  * Logic: UpperWick \>= 2 \* BodySize  
* **Measurement Start Point (จุดวัดระยะ):** ไส้เทียนของแท่งที่ 2 (แท่งถัดจาก Signal)

#### **2\. PAT 2 (2 Candles Pattern)**

* Engulfing, Harami, Tweezer  
* **Measurement Start Point:** ไส้เทียนของแท่งที่ 3

#### **3\. PAT 3 (3 Candles Pattern)**

* Morning Star, Evening Star  
* **Measurement Start Point:** ไส้เทียนของแท่งที่ 4

### **Module C: Context Filtering (การกรองสัญญาณเชิงบริบท)**

ต้องมีการตรวจสอบ Location ของราคาเทียบกับ Support/Resistance (S/R) ก่อนยืนยันสัญญาณ

#### **Logic: "PA Wrong Place" (PA เกิดผิดที่) \-\> Reverse Signal**

* **Case 1: Headbutting Resistance (หัวโหม่งต้าน)**  
  * *Detect:* พบ Buy Signal (เช่น Hammer) ที่บริเวณ Resistance Zone (หรือ Krob สำคัญ)  
  * *Action:* **IGNORE Buy Signal** \-\> **Prepare SELL Signal** (Reversal Trade)  
* **Case 2: Headbutting Support (หัวโหม่งรับ)**  
  * *Detect:* พบ Sell Signal (เช่น Shooting Star) ที่บริเวณ Support Zone  
  * *Action:* **IGNORE Sell Signal** \-\> **Prepare BUY Signal** (Reversal Trade)

#### **Logic: Sig Chon Sig (ซิกชนซิก)**

* *Detect:* มี Active Signal ฝั่ง Buy และ Sell เกิดขึ้นพร้อมกันในระยะเวลาใกล้เคียงกัน หรือยังไม่จบ Cycle ทั้งคู่  
* *Action:* **NO TRADE** (Market is Sideways/Indecisive)

### **Module D: Execution & Management (การจัดการออเดอร์)**

#### **1\. Entry Trigger**

* เมื่อ State \= SIGNAL\_DETECTED  
* ผ่านการกรอง Context Filtering  
* รอ Confirmation Candles (Configurable: 1-4 แท่ง)

#### **2\. Invalidation (Stop Loss Logic)**

* **Condition:** "Tamlai Sai Lang Sig" (ทำลายไส้หลังซิก)  
* **Logic:**  
  * Buy Order: CurrentPrice \< Lowest\_Low\_Of\_Signal\_Pattern  
  * Sell Order: CurrentPrice \> Highest\_High\_Of\_Signal\_Pattern  
* **Action:** Close Position immediately (Cut Loss).

#### **3\. Take Profit (TP Logic)**

* **Calculation:** EntryPrice \+ (Direction \* Rob\_Distance)  
  * *Rob\_Distance* อ้างอิงจากตารางในข้อ 2.1  
* **Measurement Origin:** เริ่มวัดระยะจาก "Measurement Start Point" ของแต่ละ PAT (ไม่ใช่ราคาเปิดของแท่ง Signal)

#### **4\. Re-entry (Sig Kam Sig)**

* **Condition:**  
  1. Signal แรกวิ่งชน TP (100%) แล้ว  
  2. เกิด Signal ใหม่ในทิศทางเดิม (Trend Follow)  
* **Action:** เปิด Order เพิ่ม (Scale in) โดยใช้ Logic การเข้าเทรดเดิม

## **4\. Pseudocode Example (ตัวอย่างโครงสร้างโค้ด)**

class MPPK\_Strategy:  
    def \_\_init\_\_(self, timeframe):  
        self.timeframe \= timeframe  
        self.state \= "IDLE"  
        self.tp\_target \= self.get\_tp\_distance(timeframe)  
      
    def on\_bar\_close(self, current\_candle, history):  
        \# 1\. Filter Timeframe  
        if self.timeframe not in \["H1", "H4", "D1", "W1", "MN"\]:  
            return

        \# 2\. Pattern Recognition  
        pattern \= self.detect\_pa\_pattern(history) \# Returns PAT1, PAT2, PAT3 or None  
          
        \# 3\. Context Check (Wrong Place / Krob)  
        valid\_signal \= self.check\_context(pattern, current\_candle.price)  
          
        if valid\_signal:  
            \# 4\. Invalidation Check (Tamlai Sai Lang Sig)  
            if self.is\_invalidated(valid\_signal, current\_candle):  
                self.state \= "IDLE"  
                return

            \# 5\. Entry Logic  
            if self.state \== "IDLE" or self.state \== "REST":  
                 self.execute\_trade(valid\_signal)  
                 self.state \= "ACTIVE"  
              
            \# 6\. Re-entry Logic (Sig Kam Sig)  
            elif self.state \== "ACTIVE" and self.check\_previous\_tp\_hit():  
                 self.execute\_trade(valid\_signal) \# Stack order  
          
        \# 7\. Exit Logic  
        self.manage\_active\_trades(current\_candle)

    def manage\_active\_trades(self, current\_candle):  
        for trade in self.active\_trades:  
            \# Check TP (Rob)  
            if self.distance(trade.entry, current\_candle.close) \>= self.tp\_target:  
                self.close\_trade(trade, reason="TP Hit")  
                self.state \= "REST" \# Enter Pullback analysis mode  
              
            \# Check Invalidation (Tamlai Sai Lang Sig)  
            if self.check\_break\_wick(trade, current\_candle):  
                self.close\_trade(trade, reason="Invalidated")  
                self.state \= "IDLE"  
