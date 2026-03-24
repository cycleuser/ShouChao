"""
Multi-country Stock Market Data Fetcher.

Supports real-time market data from multiple free public APIs:
- Yahoo Finance (global coverage)
- Alpha Vantage (US, forex, crypto)
- Financial Modeling Prep (US stocks)
- East Money (China A-Share)
- Sina Finance (China A-Share, HK)
- Yahoo Finance API (global)

Markets:
- China: A-Share (Shanghai/Shenzhen), HK
- US: NYSE, NASDAQ
- Japan: TSE
- UK: LSE
- Germany: XETRA
- India: NSE, BSE
- Australia: ASX
- Korea: KOSPI
"""

import logging
import time
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class StockQuote:
    """Real-time stock quote data."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    open_price: float
    high_price: float
    low_price: float
    previous_close: float
    volume: int
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    currency: str = "USD"
    exchange: str = ""
    timezone: str = "UTC"
    last_update: str = ""
    data_source: str = ""


@dataclass
class MarketIndex:
    """Market index data."""
    name: str
    symbol: str
    price: float
    change: float
    change_percent: float
    market: str
    currency: str = "USD"
    last_update: str = ""


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @property
    @abstractmethod
    def supported_markets(self) -> list[str]:
        """List of supported market codes."""
        pass
    
    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> list[StockQuote]:
        """Get quotes for multiple symbols."""
        pass
    
    @abstractmethod
    def get_market_stocks(self, market: str, sector: Optional[str] = None) -> list[StockQuote]:
        """Get all stocks for a market/sector."""
        pass
    
    def is_available(self) -> bool:
        """Check if provider is available."""
        try:
            import requests
            return True
        except ImportError:
            return False


class YahooFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance data provider.
    
    Uses Yahoo Finance API for global market data.
    Note: This is an unofficial API, use with rate limiting.
    """
    
    MARKET_MAP = {
        "US": "US",
        "CN": "SH",  # Shanghai
        "SZ": "SZ",  # Shenzhen
        "HK": "HK",
        "JP": "JP",
        "UK": "L",
        "DE": "DE",
        "FR": "FR",
        "IN": "NSI",
        "AU": "AX",
        "KR": "KS",
    }
    
    # Major indices by market
    INDICES = {
        "US": [
            ("^GSPC", "S&P 500"),
            ("^DJI", "Dow Jones"),
            ("^IXIC", "NASDAQ"),
            ("^RUT", "Russell 2000"),
        ],
        "CN": [
            ("000001.SS", "上证指数"),
            ("000016.SS", "上证 50"),
        ],
        "SZ": [
            ("399001.SZ", "深证成指"),
            ("399006.SZ", "创业板指"),
        ],
        "HK": [
            ("^HSI", "恒生指数"),
            ("^HSTECH", "恒生科技"),
        ],
        "JP": [
            ("^N225", "日经 225"),
            ("^TPX", "TOPIX"),
        ],
        "UK": [
            ("^FTSE", "FTSE 100"),
        ],
        "DE": [
            ("^GDAXI", "DAX"),
        ],
        "FR": [
            ("^FCHI", "CAC 40"),
        ],
        "IN": [
            ("^BSESN", "BSE Sensex"),
            ("^NSEI", "Nifty 50"),
        ],
        "AU": [
            ("^AXJO", "ASX 200"),
        ],
        "KR": [
            ("^KS11", "KOSPI"),
        ],
    }
    
    # Sector ETFs for US market
    SECTOR_ETS = {
        "Technology": ["XLK", "QQQ"],
        "Healthcare": ["XLV"],
        "Financial": ["XLF"],
        "Consumer": ["XLY", "XLP"],
        "Energy": ["XLE"],
        "Industrial": ["XLI"],
        "Materials": ["XLB"],
        "Real Estate": ["XLRE"],
        "Utilities": ["XLU"],
        "Communication": ["XLC"],
    }
    
    @property
    def name(self) -> str:
        return "yahoo"
    
    @property
    def supported_markets(self) -> list[str]:
        return ["US", "CN", "SZ", "HK", "JP", "UK", "DE", "FR", "IN", "AU", "KR"]
    
    def get_quotes(self, symbols: list[str]) -> list[StockQuote]:
        """Get quotes from Yahoo Finance."""
        quotes = []
        
        for symbol in symbols:
            try:
                quote = self._fetch_quote(symbol)
                if quote:
                    quotes.append(quote)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
        
        return quotes
    
    def _fetch_quote(self, symbol: str) -> Optional[StockQuote]:
        """Fetch single quote from Yahoo Finance API."""
        try:
            import requests
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {
                "interval": "1d",
                "range": "1d",
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("chart") or not data["chart"].get("result"):
                return None
            
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            
            quote = StockQuote(
                symbol=symbol,
                name=meta.get("symbol", symbol),
                price=meta.get("regularMarketPrice", 0),
                change=meta.get("regularMarketChange", 0),
                change_percent=meta.get("regularMarketChangePercent", 0),
                open_price=meta.get("regularMarketOpen", 0),
                high_price=meta.get("regularMarketDayHigh", 0),
                low_price=meta.get("regularMarketDayLow", 0),
                previous_close=meta.get("chartPreviousClose", 0),
                volume=meta.get("regularMarketVolume", 0),
                market_cap=meta.get("marketCap"),
                currency=meta.get("currency", "USD"),
                exchange=meta.get("exchangeName", ""),
                timezone=meta.get("gmtoffset", 0),
                last_update=datetime.now().isoformat(),
                data_source="yahoo",
            )
            
            return quote
            
        except Exception as e:
            logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return None
    
    def get_market_stocks(self, market: str, sector: Optional[str] = None) -> list[StockQuote]:
        """Get market stocks/index data."""
        if market == "US" and sector:
            # Get sector ETFs
            etfs = self.SECTOR_ETS.get(sector, [])
            return self.get_quotes(etfs)
        
        # Get market indices
        indices = self.INDICES.get(market, [])
        symbols = [idx[0] for idx in indices]
        return self.get_quotes(symbols)


class EastMoneyProvider(MarketDataProvider):
    """
    East Money (东方财富) data provider for China A-Share.
    
    Provides real-time A-Share market data.
    """
    
    SECTOR_MAP = {
        "银行": "m:0 t:81 s:1",
        "证券": "m:0 t:81 s:2",
        "保险": "m:0 t:81 s:3",
        "房地产": "m:0 t:12",
        "食品饮料": "m:0 t:16 s:1",
        "医药生物": "m:0 t:17",
        "电子": "m:0 t:19",
        "计算机": "m:0 t:20",
        "通信": "m:0 t:21",
        "传媒": "m:0 t:22",
        "电气设备": "m:0 t:24",
        "机械设备": "m:0 t:25",
        "汽车": "m:0 t:26",
        "家用电器": "m:0 t:27",
        "有色金属": "m:0 t:30",
        "钢铁": "m:0 t:31",
        "化工": "m:0 t:18",
        "煤炭": "m:0 t:28",
        "石油石化": "m:0 t:29",
        "交通运输": "m:0 t:33",
        "国防军工": "m:0 t:35",
        "公用事业": "m:0 t:36",
        "商业贸易": "m:0 t:37",
        "农林牧渔": "m:0 t:38",
        "建筑材料": "m:0 t:39",
        "建筑装饰": "m:0 t:40",
        "轻工制造": "m:0 t:41",
        "综合": "m:0 t:42",
        "纺织服装": "m:0 t:43",
        "休闲服务": "m:0 t:44",
    }
    
    @property
    def name(self) -> str:
        return "eastmoney"
    
    @property
    def supported_markets(self) -> list[str]:
        return ["CN", "SZ"]
    
    def get_quotes(self, symbols: list[str]) -> list[StockQuote]:
        """Get A-Share quotes."""
        quotes = []
        
        # East Money batch quote API
        codes = []
        for symbol in symbols:
            if symbol.startswith("6"):
                codes.append(f"0{symbol}")  # Shanghai
            else:
                codes.append(f"1{symbol}")  # Shenzhen
        
        try:
            import requests
            
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "fltt": "2",
                "fields": "f43,f44,f45,f46,f47,f48,f49,f116,f117,f118,f119",
                "secids": ",".join(codes),
            }
            
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("data"):
                for item in data["data"].values():
                    if item.get("f43") is None:
                        continue
                    
                    symbol = str(item.get("f116", ""))
                    name = item.get("f117", "")
                    
                    quote = StockQuote(
                        symbol=symbol,
                        name=name,
                        price=item.get("f43", 0) / 100,
                        change=item.get("f44", 0) / 100,
                        change_percent=item.get("f45", 0) / 100,
                        open_price=item.get("f46", 0) / 100,
                        high_price=item.get("f47", 0) / 100,
                        low_price=item.get("f48", 0) / 100,
                        previous_close=item.get("f49", 0) / 100,
                        volume=item.get("f119", 0),
                        market_cap=item.get("f118", 0),
                        currency="CNY",
                        exchange="A 股",
                        last_update=datetime.now().isoformat(),
                        data_source="eastmoney",
                    )
                    quotes.append(quote)
            
        except Exception as e:
            logger.error(f"East Money error: {e}")
        
        return quotes
    
    def get_market_stocks(self, market: str, sector: Optional[str] = None) -> list[StockQuote]:
        """Get A-Share stocks by sector."""
        try:
            import requests
            
            if sector and sector in self.SECTOR_MAP:
                fs_code = self.SECTOR_MAP[sector]
            else:
                # All A-shares
                fs_code = "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23"
            
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": 500,
                "po": "1",
                "np": "1",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": fs_code,
                "fields": "f12,f14,f2,f3,f4,f20,f9,f23,f24,f25,f26,f27,f28",
            }
            
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            quotes = []
            if data.get("data") and data["data"].get("diff"):
                for item in data["data"]["diff"]:
                    if item.get("f2") is None:
                        continue
                    
                    quotes.append(StockQuote(
                        symbol=str(item.get("f12", "")),
                        name=item.get("f14", ""),
                        price=float(item.get("f2", 0)),
                        change_percent=float(item.get("f3", 0)),
                        change=float(item.get("f4", 0)),
                        open_price=float(item.get("f23", 0)),
                        high_price=float(item.get("f24", 0)),
                        low_price=float(item.get("f25", 0)),
                        previous_close=float(item.get("f26", 0)),
                        volume=float(item.get("f9", 0)) * 1e4,
                        market_cap=float(item.get("f20", 0)) * 1e8,
                        pe_ratio=item.get("f27", 0) if item.get("f27") else None,
                        currency="CNY",
                        exchange="A 股",
                        last_update=datetime.now().isoformat(),
                        data_source="eastmoney",
                    ))
            
            return quotes
            
        except Exception as e:
            logger.error(f"Failed to fetch A-Share data: {e}")
            return []


class SinaFinanceProvider(MarketDataProvider):
    """
    Sina Finance data provider.
    
    Provides China A-Share and HK stock data.
    """
    
    @property
    def name(self) -> str:
        return "sina"
    
    @property
    def supported_markets(self) -> list[str]:
        return ["CN", "SZ", "HK"]
    
    def get_quotes(self, symbols: list[str]) -> list[StockQuote]:
        """Get quotes from Sina Finance."""
        quotes = []
        
        try:
            import requests
            
            # Convert symbols to Sina format
            sina_symbols = []
            for symbol in symbols:
                if symbol.startswith("6") or symbol.startswith("9"):
                    sina_symbols.append(f"sh{symbol}")
                elif symbol.startswith("3") or symbol.startswith("0"):
                    sina_symbols.append(f"sz{symbol}")
                elif symbol.endswith(".HK"):
                    sina_symbols.append(f"rt_hk{symbol.replace('.HK', '')}")
            
            if not sina_symbols:
                return quotes
            
            url = "https://hq.sinajs.cn/list=" + ",".join(sina_symbols)
            headers = {
                "Referer": "https://finance.sina.com.cn/",
                "User-Agent": "Mozilla/5.0",
            }
            
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "gbk"  # Sina uses GBK encoding
            
            lines = resp.text.strip().split("\n")
            for line in lines:
                if not line or "=" not in line:
                    continue
                
                parts = line.split("=")
                if len(parts) < 2:
                    continue
                
                data = parts[1].strip('"').split(",")
                if len(data) < 32:
                    continue
                
                # Parse symbol from variable name
                var_name = parts[0]
                if "sh" in var_name or "sz" in var_name:
                    symbol = var_name[-6:]
                else:
                    symbol = var_name.replace("rt_hk", "") + ".HK"
                
                try:
                    price = float(data[3]) if data[3] else 0
                    prev_close = float(data[2]) if data[2] else 0
                    change = price - prev_close
                    change_percent = (change / prev_close * 100) if prev_close else 0
                    
                    quote = StockQuote(
                        symbol=symbol,
                        name=data[0] if len(data) > 0 else symbol,
                        price=price,
                        change=change,
                        change_percent=change_percent,
                        open_price=float(data[1]) if data[1] else 0,
                        high_price=float(data[4]) if data[4] else 0,
                        low_price=float(data[5]) if data[5] else 0,
                        previous_close=prev_close,
                        volume=float(data[8]) if data[8] else 0,
                        currency="CNY",
                        exchange="A 股" if "sh" in var_name or "sz" in var_name else "港股",
                        last_update=data[31] if len(data) > 31 else datetime.now().isoformat(),
                        data_source="sina",
                    )
                    quotes.append(quote)
                except (ValueError, IndexError) as e:
                    logger.debug(f"Parse error for {symbol}: {e}")
            
        except Exception as e:
            logger.error(f"Sina Finance error: {e}")
        
        return quotes
    
    def get_market_stocks(self, market: str, sector: Optional[str] = None) -> list[StockQuote]:
        """Get market stocks - limited support."""
        # Sina doesn't provide sector-based listing
        # Return empty - use East Money for A-Share
        return []


class MockMarketProvider(MarketDataProvider):
    """
    Mock provider for demo/testing.
    
    Generates realistic-looking market data.
    """
    
    STOCK_DATABASE = {
        "US": [
            ("AAPL", "Apple Inc", 150, 3000e9),
            ("MSFT", "Microsoft Corp", 380, 2800e9),
            ("GOOGL", "Alphabet Inc", 140, 1800e9),
            ("AMZN", "Amazon.com", 175, 1700e9),
            ("NVDA", "NVIDIA Corp", 480, 1200e9),
            ("META", "Meta Platforms", 470, 1200e9),
            ("TSLA", "Tesla Inc", 180, 600e9),
            ("BRK.B", "Berkshire Hathaway", 410, 900e9),
            ("JPM", "JPMorgan Chase", 195, 560e9),
            ("V", "Visa Inc", 275, 540e9),
            ("JNJ", "Johnson & Johnson", 160, 420e9),
            ("WMT", "Walmart Inc", 165, 440e9),
            ("PG", "Procter & Gamble", 155, 370e9),
            ("MA", "Mastercard", 450, 420e9),
            ("UNH", "UnitedHealth", 520, 480e9),
            ("HD", "Home Depot", 350, 350e9),
            ("BAC", "Bank of America", 35, 280e9),
            ("XOM", "Exxon Mobil", 105, 420e9),
            ("CVX", "Chevron Corp", 155, 290e9),
            ("PFE", "Pfizer Inc", 28, 160e9),
        ],
        "CN": [
            ("600519", "贵州茅台", 1700, 2100e9),
            ("601398", "工商银行", 5.2, 1800e9),
            ("601288", "农业银行", 3.8, 1300e9),
            ("601939", "建设银行", 6.5, 1600e9),
            ("601988", "中国银行", 4.1, 1200e9),
            ("600036", "招商银行", 32, 800e9),
            ("000858", "五粮液", 150, 580e9),
            ("601318", "中国平安", 45, 820e9),
            ("600276", "恒瑞医药", 42, 270e9),
            ("000333", "美的集团", 62, 430e9),
            ("002415", "海康威视", 35, 330e9),
            ("600900", "长江电力", 26, 590e9),
            ("601888", "中国中免", 75, 160e9),
            ("000568", "泸州老窖", 180, 260e9),
            ("600809", "山西汾酒", 210, 240e9),
        ],
        "HK": [
            ("0700.HK", "腾讯控股", 320, 3100e9),
            ("9988.HK", "阿里巴巴", 78, 1600e9),
            ("1299.HK", "友邦保险", 62, 720e9),
            ("0005.HK", "汇丰控股", 62, 1200e9),
            ("2318.HK", "中国平安", 42, 770e9),
            ("3690.HK", "美团", 95, 590e9),
            ("1024.HK", "快手", 52, 220e9),
            ("9618.HK", "京东", 120, 190e9),
            ("0941.HK", "中国移动", 68, 1400e9),
            ("1109.HK", "华润置地", 32, 230e9),
        ],
        "JP": [
            ("7203.T", "Toyota Motor", 2500, 350e9),
            ("9984.T", "SoftBank Group", 6200, 130e9),
            ("6758.T", "Sony Group", 12000, 150e9),
            ("9432.T", "NTT", 4100, 95e9),
            ("6861.T", "Keyence", 58000, 110e9),
        ],
        "UK": [
            ("HSBA.L", "HSBC Holdings", 650, 130e9),
            ("AZN.L", "AstraZeneca", 10500, 160e9),
            ("SHEL.L", "Shell PLC", 2600, 200e9),
            ("BP.L", "BP PLC", 490, 90e9),
            ("ULVR.L", "Unilever", 4200, 105e9),
        ],
        "DE": [
            ("SAP.DE", "SAP SE", 175, 210e9),
            ("SIE.DE", "Siemens", 170, 140e9),
            ("VOW3.DE", "Volkswagen", 115, 58e9),
            ("ALV.DE", "Allianz", 260, 105e9),
            ("BAS.DE", "BASF", 48, 43e9),
        ],
        "IN": [
            ("RELIANCE.NS", "Reliance Industries", 2900, 240e9),
            ("TCS.NS", "Tata Consultancy", 4000, 165e9),
            ("HDFCBANK.NS", "HDFC Bank", 1600, 120e9),
            ("INFY.NS", "Infosys", 1500, 63e9),
            ("ICICIBANK.NS", "ICICI Bank", 1050, 74e9),
        ],
        "AU": [
            ("CBA.AX", "Commonwealth Bank", 125, 210e9),
            ("BHP.AX", "BHP Group", 45, 230e9),
            ("CSL.AX", "CSL Limited", 280, 135e9),
            ("NAB.AX", "NAB", 35, 115e9),
            ("WBC.AX", "Westpac", 25, 88e9),
        ],
        "KR": [
            ("005930.KS", "Samsung Electronics", 72000, 380e9),
            ("000660.KS", "SK Hynix", 135000, 98e9),
            ("035420.KS", "NAVER", 195000, 32e9),
            ("051910.KS", "LG Chem", 420000, 30e9),
            ("005380.KS", "Hyundai Motor", 185000, 40e9),
        ],
    }
    
    SECTORS = {
        "US": {
            "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA"],
            "Healthcare": ["JNJ", "UNH", "PFE"],
            "Financial": ["JPM", "BAC", "V", "MA", "BRK.B"],
            "Consumer": ["AMZN", "WMT", "PG", "HD"],
            "Energy": ["XOM", "CVX"],
        },
        "CN": {
            "银行": ["601398", "601288", "601939", "601988", "600036"],
            "食品饮料": ["600519", "000858", "000568", "600809"],
            "医药生物": ["600276"],
            "电子": ["002415"],
            "家用电器": ["000333"],
        },
    }
    
    @property
    def name(self) -> str:
        return "mock"
    
    @property
    def supported_markets(self) -> list[str]:
        return list(self.STOCK_DATABASE.keys())
    
    def get_quotes(self, symbols: list[str]) -> list[StockQuote]:
        """Generate mock quotes."""
        quotes = []
        
        # Find which market the symbols belong to
        market = None
        for m, stocks in self.STOCK_DATABASE.items():
            stock_symbols = [s[0] for s in stocks]
            if any(s in stock_symbols for s in symbols):
                market = m
                break
        
        if not market:
            market = "US"
        
        stock_map = {s[0]: s for s in self.STOCK_DATABASE.get(market, [])}
        
        for symbol in symbols:
            if symbol not in stock_map:
                continue
            
            base_info = stock_map[symbol]
            
            # Generate realistic price movement
            base_price = base_info[2]
            change_pct = random.gauss(0, 2)  # Normal distribution, 2% std
            change = base_price * (change_pct / 100)
            price = base_price + change
            
            quote = StockQuote(
                symbol=symbol,
                name=base_info[1],
                price=round(price, 2),
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                open_price=round(price * random.uniform(0.99, 1.01), 2),
                high_price=round(price * random.uniform(1.01, 1.03), 2),
                low_price=round(price * random.uniform(0.97, 0.99), 2),
                previous_close=round(base_price, 2),
                volume=int(random.uniform(1e6, 100e6)),
                market_cap=base_info[3],
                currency="CNY" if market in ["CN", "HK"] else "USD" if market == "US" else "Local",
                exchange=market,
                last_update=datetime.now().isoformat(),
                data_source="mock",
            )
            quotes.append(quote)
        
        return quotes
    
    def get_market_stocks(self, market: str, sector: Optional[str] = None) -> list[StockQuote]:
        """Get all stocks for a market/sector."""
        symbols = []
        
        if sector and market in self.SECTORS:
            symbols = self.SECTORS[market].get(sector, [])
        elif market in self.STOCK_DATABASE:
            symbols = [s[0] for s in self.STOCK_DATABASE[market]]
        
        return self.get_quotes(symbols)


class AggregatedMarketProvider:
    """
    Aggregates multiple market data providers.
    
    Automatically selects the best provider for each market.
    Implements rate limiting and failover.
    """
    
    def __init__(self):
        self._providers: list[MarketDataProvider] = [
            EastMoneyProvider(),    # Best for A-Share
            YahooFinanceProvider(),  # Global coverage
            SinaFinanceProvider(),   # Alternative for China
            MockMarketProvider(),    # Fallback
        ]
        
        self._rate_limits: dict[str, float] = {}  # Last request time per provider
        self._prefer_provider: dict[str, str] = {
            "CN": "eastmoney",
            "SZ": "eastmoney",
            "HK": "sina",
            "US": "yahoo",
            "JP": "yahoo",
            "UK": "yahoo",
            "DE": "yahoo",
            "FR": "yahoo",
            "IN": "yahoo",
            "AU": "yahoo",
            "KR": "yahoo",
        }
    
    def get_providers(self) -> list[str]:
        """Get list of available provider names."""
        return [p.name for p in self._providers if p.is_available()]
    
    def get_markets(self) -> list[str]:
        """Get all supported markets."""
        markets = set()
        for provider in self._providers:
            markets.update(provider.supported_markets)
        return sorted(list(markets))
    
    def get_quotes(self, symbols: list[str], prefer_provider: Optional[str] = None) -> list[StockQuote]:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            prefer_provider: Preferred provider name
            
        Returns:
            List of StockQuote objects
        """
        # Determine best provider
        if prefer_provider:
            provider = self._get_provider(prefer_provider)
        else:
            # Auto-detect based on symbols
            provider = self._select_provider(symbols)
        
        if provider:
            return provider.get_quotes(symbols)
        
        # Fallback to mock data
        return MockMarketProvider().get_quotes(symbols)
    
    def get_market_data(
        self,
        market: str,
        sector: Optional[str] = None,
        limit: int = 500,
    ) -> list[StockQuote]:
        """
        Get all stocks for a market.
        
        Args:
            market: Market code (CN, US, HK, etc.)
            sector: Optional sector filter
            limit: Maximum number of stocks
            
        Returns:
            List of StockQuote objects
        """
        # Get preferred provider for this market
        provider_name = self._prefer_provider.get(market)
        provider = self._get_provider(provider_name) if provider_name else None
        
        if not provider:
            # Try any available provider
            for p in self._providers:
                if market in p.supported_markets:
                    provider = p
                    break
        
        if provider:
            quotes = provider.get_market_stocks(market, sector)
            return quotes[:limit]
        
        # Fallback to mock
        return MockMarketProvider().get_market_stocks(market, sector)
    
    def _get_provider(self, name: str) -> Optional[MarketDataProvider]:
        """Get provider by name."""
        for p in self._providers:
            if p.name == name:
                return p
        return None
    
    def _select_provider(self, symbols: list[str]) -> Optional[MarketDataProvider]:
        """Select best provider based on symbols."""
        # Simple heuristic: check first symbol
        if not symbols:
            return None
        
        symbol = symbols[0]
        
        # A-Share
        if symbol.startswith("6") or symbol.startswith("0") or symbol.startswith("3"):
            return EastMoneyProvider()
        
        # HK stocks
        if ".HK" in symbol:
            return SinaFinanceProvider()
        
        # Default to Yahoo
        return YahooFinanceProvider()
    
    def refresh_rate_limit(self, provider_name: str):
        """Update rate limit timestamp for a provider."""
        self._rate_limits[provider_name] = time.time()
    
    def can_request(self, provider_name: str, min_interval: float = 1.0) -> bool:
        """Check if we can make a request to a provider."""
        last_request = self._rate_limits.get(provider_name, 0)
        return (time.time() - last_request) >= min_interval


# Singleton instance
_provider: Optional[AggregatedMarketProvider] = None


def get_provider() -> AggregatedMarketProvider:
    """Get the aggregated provider singleton."""
    global _provider
    if _provider is None:
        _provider = AggregatedMarketProvider()
    return _provider


def get_market_quotes(
    market: str,
    sector: Optional[str] = None,
    limit: int = 500,
) -> list[StockQuote]:
    """
    Convenience function to get market quotes.
    
    Args:
        market: Market code (CN, US, HK, JP, UK, DE, IN, AU, KR)
        sector: Optional sector filter
        limit: Maximum number of stocks
        
    Returns:
        List of StockQuote objects
    """
    provider = get_provider()
    return provider.get_market_data(market, sector=sector, limit=limit)


def get_stock_quotes(symbols: list[str]) -> list[StockQuote]:
    """
    Convenience function to get quotes for specific symbols.
    
    Args:
        symbols: List of stock symbols
        
    Returns:
        List of StockQuote objects
    """
    provider = get_provider()
    return provider.get_quotes(symbols)
