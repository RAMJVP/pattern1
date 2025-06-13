import pandas as pd
import pandas_ta as ta
import yfinance as yf
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()


# Allow frontend to access backend

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888"],  # or set ["http://localhost:8888"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OHLCRequest(BaseModel):
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]

@app.post("/detect")
def detect(req: OHLCRequest):
    df = pd.DataFrame({
        "open": req.open, "high": req.high, "low": req.low, "close": req.close
    })
    df["bullish_engulfing"] = ta.cdl.bullish_engulfing(df["open"], df["high"], df["low"], df["close"])
    return {"pattern": df["bullish_engulfing"].tolist()}





class PatternInput(BaseModel):
    event: str
    nifty: float
    rsi: float
    vix: float
    oiChange: float

class PatternOutput(BaseModel):
    pattern: str
    signal: str
    confidence: float
    reason: str

def get_nifty_ohlcv(days: int = 20) -> pd.DataFrame:
    df = yf.Ticker("^NSEI").history(period=f"{days}d", interval="1d")
    if df.empty:
        raise RuntimeError("Failed to fetch NIFTY data")
    return df[["Open", "High", "Low", "Close", "Volume"]].rename(str.lower, axis=1)

@app.post("/api/pattern-detect", response_model=PatternOutput)
def detect_pattern(data: PatternInput):
    df = get_nifty_ohlcv()

    # Apply Bullish Harami
    df["bullish_harami"] = ta.cdl_pattern(
        name="cdl_harami",  # Correct lowercase pattern name
        open_=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )

    # Apply Bullish Engulfing
    df["engulfing"] = ta.cdl_pattern(
        name="cdl_engulfing",  # Correct lowercase pattern name
        open_=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"]
    )

    last = df.iloc[-1]
    pattern = "None"
    signal = "WAIT"
    confidence = 55.0
    reason = f"No pattern detected. RSI={data.rsi}, VIX={data.vix}, OI Change={data.oiChange}%"

    if last["bullish_harami"] != 0:
        pattern = "Bullish Harami"
        signal = "BUY CE"
        confidence = 85.0 if data.rsi < 40 else 70.0
        reason = f"{pattern} + RSI={data.rsi}, VIX={data.vix}, OI Change={data.oiChange}%"

    elif last["engulfing"] != 0:
        pattern = "Engulfing"
        signal = "BUY CE" if data.rsi < 50 else "SELL PE"
        confidence = 80.0
        reason = f"{pattern} + RSI={data.rsi}, VIX={data.vix}, OI Change={data.oiChange}%"

    return PatternOutput(pattern=pattern, signal=signal, confidence=confidence, reason=reason)




