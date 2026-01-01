import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import json
import os
from typing import Dict, List, Tuple, Optional, Any

class OLYMPUSIntelligenceEngine:
    """
    Advanced Intelligence Engine for Project MTF - OLYMPUS
    Mimics Mxwll Price Action Suite & Prepares data for AI Training (LSTM/Transformer)
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Expects a DataFrame with columns: ['open', 'high', 'low', 'close', 'volume']
        Index should be datetime
        """
        self.df = data.copy()
        self._ensure_indicators()

    def _ensure_indicators(self):
        """คำนวณตัวชี้วัดพื้นฐานที่จำเป็นสำหรับการวิเคราะห์ทางยุทธวิธี"""
        # 1. ATR (Average True Range) - สำหรับวัด Blast Radius
        high_low = self.df['high'] - self.df['low']
        high_close = np.abs(self.df['high'] - self.df['close'].shift())
        low_close = np.abs(self.df['low'] - self.df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        self.df['atr'] = true_range.rolling(14).mean()

        # 2. ADX (Average Directional Index) - สำหรับวัด Invasion Strength
        up_move = self.df['high'].diff()
        down_move = self.df['low'].diff(-1)
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        self.df['plus_di'] = 100 * (pd.Series(plus_dm).rolling(14).mean() / self.df['atr'])
        self.df['minus_di'] = 100 * (pd.Series(minus_dm).rolling(14).mean() / self.df['atr'])
        dx = 100 * np.abs(self.df['plus_di'] - self.df['minus_di']) / (self.df['plus_di'] + self.df['minus_di'])
        self.df['adx'] = dx.rolling(14).mean()

    def get_market_session(self) -> Dict[str, Any]:
        """ระบุ Session ปัจจุบัน (NY Time)"""
        ny_tz = pytz.timezone('America/New_York')
        now = datetime.now(ny_tz)
        hour, minute = now.hour, now.minute
        
        def is_in_range(sh, sm, eh, em):
            start = sh * 60 + sm
            end = eh * 60 + em
            current = hour * 60 + minute
            if end >= start:
                return start <= current <= end
            return current >= start or current <= end

        session = "Dead Zone"
        color = "gray"
        
        if is_in_range(9, 30, 16, 0):
            session, color = "New York", "#f24968"
        elif is_in_range(20, 0, 2, 0):
            session, color = "Asia", "#14D990"
        elif is_in_range(3, 0, 11, 30):
            session, color = "London", "#F2B807"
            
        return {"session": session, "color": color, "hour": hour, "minute": minute}

    def calculate_pivots(self, length: int) -> pd.DataFrame:
        """ระบุจุด Swing High/Low"""
        self.df['rolling_max'] = self.df['high'].rolling(window=length, center=False).max().shift(1)
        self.df['rolling_min'] = self.df['low'].rolling(window=length, center=False).min().shift(1)
        
        self.df['top_swing'] = np.where(self.df['high'] > self.df['rolling_max'], self.df['high'], 0)
        self.df['bot_swing'] = np.where(self.df['low'] < self.df['rolling_min'], self.df['low'], 0)
        
        return self.df[['top_swing', 'bot_swing']]

    def get_auto_fibs(self, sensitivity: int = 25) -> Dict[str, float]:
        """คำนวณ Fibonacci Levels จาก Swing ล่าสุด"""
        pivots = self.calculate_pivots(sensitivity)
        highs = pivots[pivots['top_swing'] > 0]
        lows = pivots[pivots['bot_swing'] > 0]
        
        if highs.empty or lows.empty:
            return {}

        last_h = highs['top_swing'].iloc[-1]
        last_l = lows['bot_swing'].iloc[-1]
        diff = last_h - last_l
        
        return {
            "0.0": last_l if last_h > last_l else last_h,
            "0.236": last_l + (diff * 0.236) if last_h > last_l else last_h - (diff * 0.236),
            "0.382": last_l + (diff * 0.382) if last_h > last_l else last_h - (diff * 0.382),
            "0.500": last_l + (diff * 0.5) if last_h > last_l else last_h - (diff * 0.5),
            "0.618": last_l + (diff * 0.618) if last_h > last_l else last_h - (diff * 0.618),
            "0.786": last_l + (diff * 0.786) if last_h > last_l else last_h - (diff * 0.786),
            "1.0": last_h if last_h > last_l else last_l
        }

    def get_volume_activity(self, lookback: int = 100) -> Dict[str, Any]:
        """จัดอันดับวอลุ่มปัจจุบันเทียบกับอดีต"""
        recent_vol = self.df['volume'].iloc[-1]
        vol_history = self.df['volume'].tail(lookback)
        p_rank = (vol_history < recent_vol).mean() * 100
        
        status = "Average"
        if p_rank <= 10: status = "Very Low"
        elif p_rank <= 33: status = "Low"
        elif p_rank <= 66: status = "High"
        elif p_rank > 90: status = "Very High"
        
        return {"rank": p_rank, "status": status, "current_vol": recent_vol}

    def get_state_vector(self) -> Dict[str, Any]:
        """รวบรวมข้อมูลสถานะทั้งหมดเพื่อส่งต่อให้ AI Agent หรือระบบจัดเก็บข้อมูล"""
        vol_info = self.get_volume_activity()
        session_info = self.get_market_session()
        fibs = self.get_auto_fibs()
        
        pivots = self.calculate_pivots(25)
        last_h = pivots[pivots['top_swing'] > 0]['top_swing'].iloc[-1] if not pivots[pivots['top_swing'] > 0].empty else 0
        last_l = pivots[pivots['bot_swing'] > 0]['bot_swing'].iloc[-1] if not pivots[pivots['bot_swing'] > 0].empty else 0
        
        state = {
            "timestamp": self.df.index[-1].isoformat() if hasattr(self.df.index[-1], 'isoformat') else str(self.df.index[-1]),
            "price_close": float(self.df['close'].iloc[-1]),
            "adx_strength": float(self.df['adx'].iloc[-1]),
            "atr_volatility": float(self.df['atr'].iloc[-1]),
            "volume_percentile": float(vol_info['rank']),
            "volume_status": vol_info['status'],
            "market_session": session_info['session'],
            "dist_to_high": float((last_h - self.df['close'].iloc[-1]) / self.df['close'].iloc[-1] if last_h else 0),
            "dist_to_low": float((self.df['close'].iloc[-1] - last_l) / self.df['close'].iloc[-1] if last_l else 0),
            "fib_0.618": float(fibs.get("0.618", 0)),
            "trend_direction": 1 if self.df['plus_di'].iloc[-1] > self.df['minus_di'].iloc[-1] else -1
        }
        return state

class TacticalDataLogger:
    """
    คลาสสำหรับบันทึกข้อมูลยุทธวิธี (Data Factory) 
    ใช้เก็บ State, Human Action และ Outcome เพื่อเทรน LSTM ในอนาคต
    """
    
    def __init__(self, storage_path: str = "olympus_battle_logs.json"):
        self.storage_path = storage_path
        self._initialize_storage()

    def _initialize_storage(self):
        """ตรวจสอบและสร้างไฟล์เก็บข้อมูลหากยังไม่มี"""
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def log_engagement(self, state: Dict[str, Any], action: str, commander_note: str, outcome: Optional[Dict] = None):
        """
        บันทึกการปะทะ (Engagement) ในสมรภูมิ
        state: ข้อมูลจาก get_state_vector()
        action: การตัดสินใจ (Approve/Reject/Modify)
        commander_note: เหตุผลประกอบการตัดสินใจของมนุษย์
        outcome: ผลลัพธ์ที่เกิดขึ้นภายหลัง (สามารถอัปเดตย้อนหลังได้)
        """
        entry = {
            "engagement_id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "state": state,
            "human_decision": {
                "action": action,
                "note": commander_note,
                "timestamp": datetime.now().isoformat()
            },
            "outcome": outcome if outcome else "Pending Analysis"
        }
        
        try:
            with open(self.storage_path, 'r+', encoding='utf-8') as f:
                logs = json.load(f)
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=4)
                f.truncate()
            return True
        except Exception as e:
            print(f"Error logging tactical data: {e}")
            return False

# --- Example of Human-in-the-Loop Workflow ---
if __name__ == "__main__":
    # 1. จำลองการดึงข้อมูลและวิเคราะห์ด้วย Engine
    dates = pd.date_range(start="2025-01-01", periods=100, freq='H')
    mock_df = pd.DataFrame({
        'open': np.random.uniform(2600, 2700, 100),
        'high': np.random.uniform(2650, 2750, 100),
        'low':  np.random.uniform(2550, 2650, 100),
        'close':np.random.uniform(2600, 2700, 100),
        'volume':np.random.uniform(1000, 5000, 100)
    }, index=dates)

    engine = OLYMPUSIntelligenceEngine(mock_df)
    logger = TacticalDataLogger()

    # 2. AI เสนอแผน (Strategic Proposal)
    current_state = engine.get_state_vector()
    print(f"\n[AI PROPOSAL] Session: {current_state['market_session']} | Vol Status: {current_state['volume_status']}")
    print(f"Action Suggestion: Start Grid Buy at {current_state['price_close']} near 0.618 Fib.")

    # 3. Human in the Loop (จำลองการตัดสินใจของมนุษย์)
    user_action = "Approve" 
    user_note = "Approving because price is near strong Order Block and NY Session is starting."

    # 4. บันทึกลง Data Factory
    success = logger.log_engagement(current_state, user_action, user_note)
    if success:
        print("\n[SUCCESS] Engagement logged to Tactical Data Factory.")
        print("Data is now ready for future LSTM training sequence.")