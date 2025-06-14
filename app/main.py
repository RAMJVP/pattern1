import pandas as pd
import pandas_ta as ta
import yfinance as yf
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import httpx




TWELVE_DATA_API_KEY = "663d44b03e2148c3a45e9e58f9cd6cb6"




app = FastAPI()


# Allow frontend to access backend

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888","https://admirable-smakager-729141.netlify.app","https://inspireme.in"],  # or set ["http://localhost:8888"]
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

def get_nifty_ohlcv_l(days: int = 20) -> pd.DataFrame:
    df = yf.Ticker("^NSEI").history(period=f"{days}d", interval="1d")
    if df.empty:
        raise RuntimeError("Failed to fetch NIFTY data")
    return df[["Open", "High", "Low", "Close", "Volume"]].rename(str.lower, axis=1)
    
    
    
def get_nifty_ohlcv_nw(days: int = 20) -> pd.DataFrame:
    try:
        df = yf.Ticker("^NSEI").history(period=f"{days}d", interval="1d")
        if df.empty:
            raise ValueError("Empty")
    except:
        print("[X] Failed to fetch ^NSEI. Trying fallback: NIFTYBEES.NS")
        df = yf.Ticker("NIFTYBEES.NS").history(period=f"{days}d", interval="1d")
        if df.empty:
            raise RuntimeError("Failed to fetch NIFTY data from fallback")
    
    return df[["Open", "High", "Low", "Close", "Volume"]].rename(str.lower, axis=1)





@app.post("/api/pattern-detect-l", response_model=PatternOutput)
def detect_pattern(data: PatternInput):
    df = get_nifty_ohlcv_l()

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


def get_nifty_ohlcv_td(days: int = 20) -> pd.DataFrame:
    url = f"https://api.twelvedata.com/time_series?symbol=NIFTY_50&interval=1day&outputsize={days}&apikey={TWELVE_DATA_API_KEY}"
    
    response = httpx.get(url)
    data = response.json()

    if "values" not in data:
        raise RuntimeError(f"No values found in response. Message: {data.get('message', 'No message')}")

    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"})
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df.iloc[::-1].reset_index(drop=True)
    return df



def get_nifty_ohlcv(days: int = 20) -> pd.DataFrame:
    try:
        # Try Yahoo Finance first
        df = yf.Ticker("^NSEI").history(period=f"{days}d", interval="1d")
        if not df.empty:
            return df[["Open", "High", "Low", "Close", "Volume"]].rename(str.lower, axis=1)
    except Exception as e:
        print(f"[ERROR] yfinance failed: {e}")

    # Fall back to Reliance stock (example)
    print("[INFO] Falling back to RELIANCE.NS via Twelve Data")
    url = f"https://api.twelvedata.com/time_series?symbol=RELIANCE.NS&interval=1day&outputsize={days}&apikey={TWELVE_DATA_API_KEY}"
    response = httpx.get(url)
    data = response.json()

    if "values" not in data:
        raise RuntimeError(f"No values found in response. Message: {data.get('message', 'No message')}")

    df = pd.DataFrame(data["values"])
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = df.iloc[::-1].reset_index(drop=True)
    return df


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



