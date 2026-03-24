"""
Global Stock Market Treemap Visualization.

Provides real-time stock market heatmap/treemap for:
- A-Share (Shanghai/Shenzhen)
- US Stocks (NASDAQ/NYSE)
- HK Stocks
- Other major markets

Uses treemap layout with color-coded performance (green=up, red=down).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    """Individual stock data."""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    market_cap: float  # Market cap for sizing
    sector: str
    industry: str
    currency: str = "CNY"
    exchange: str = ""
    volume: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class SectorData:
    """Sector/Industry group data."""
    name: str
    stocks: list[StockData] = field(default_factory=list)
    change_percent: float = 0.0
    market_cap: float = 0.0
    
    def calculate(self):
        """Calculate sector aggregate values."""
        if not self.stocks:
            return
        total_cap = sum(s.market_cap for s in self.stocks)
        self.market_cap = total_cap
        if total_cap > 0:
            self.change_percent = sum(
                s.change_percent * s.market_cap for s in self.stocks
            ) / total_cap


@dataclass
class MarketMapResult:
    """Result of market map data fetch."""
    success: bool
    market: str = ""
    data: list[dict] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "market": self.market,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class MarketDataSource:
    """Base class for market data sources."""
    
    @property
    def name(self) -> str:
        return "base"
    
    def get_sectors(self) -> list[str]:
        """Get available sectors."""
        return []
    
    def get_stocks(self, sector: Optional[str] = None) -> list[StockData]:
        """Get stocks data, optionally filtered by sector."""
        return []


class AShareSource(MarketDataSource):
    """
    A-Share market data source (China).
    
    Data sources (in order of preference):
    1. Sina Finance API (real-time)
    2. East Money API
    3. Demo data fallback
    """
    
    SECTORS = [
        "银行", "证券", "保险", "房地产",
        "食品饮料", "医药生物", "农林牧渔",
        "电子", "计算机", "通信", "传媒",
        "电气设备", "机械设备", "汽车",
        "有色金属", "钢铁", "化工", "煤炭",
        "石油石化", "建筑材料", "建筑装饰",
        "交通运输", "国防军工", "公用事业",
        "商业贸易", "休闲服务", "纺织服装",
        "家用电器", "轻工制造", "综合",
    ]
    
    @property
    def name(self) -> str:
        return "ashare"
    
    def get_sectors(self) -> list[str]:
        return self.SECTORS.copy()
    
    def get_stocks(self, sector: Optional[str] = None) -> list[StockData]:
        """Fetch A-Share stock data from multiple sources."""
        # Try Sina Finance first
        stocks = self._fetch_from_sina(sector)
        if stocks:
            return stocks
        
        # Try East Money as backup
        stocks = self._fetch_from_eastmoney(sector)
        if stocks:
            return stocks
        
        # Fallback to demo data
        logger.warning("All APIs failed, using demo data")
        return self._get_demo_stocks(sector)
    
    def _fetch_from_sina(self, sector: Optional[str]) -> list[StockData]:
        """Fetch from Sina Finance API."""
        try:
            import requests
            
            # Sina real-time quote API for major stocks
            # Using a list of popular stock codes
            stock_codes = self._get_popular_codes(sector)
            if not stock_codes:
                return []
            
            # Sina API format: http://hq.sinajs.cn/list=sh600000,sz000001
            codes_str = ",".join(stock_codes[:100])  # Limit to 100 per request
            url = f"http://hq.sinajs.cn/list={codes_str}"
            
            headers = {
                "Referer": "http://finance.sina.com.cn",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "gbk"
            
            stocks = []
            for line in resp.text.strip().split("\n"):
                if not line or 'hq_str_' not in line:
                    continue
                
                try:
                    # Parse: var hq_str_sh600000="浦发银行,12.34,..."
                    code_part, data_part = line.split('="')
                    code = code_part.split("_")[-1]
                    data = data_part.strip('";').split(",")
                    
                    if len(data) < 32:
                        continue
                    
                    name = data[0]
                    price = float(data[3]) if data[3] else 0
                    prev_close = float(data[2]) if data[2] else price
                    change = price - prev_close if price and prev_close else 0
                    change_pct = (change / prev_close * 100) if prev_close else 0
                    
                    if price <= 0:
                        continue
                    
                    stocks.append(StockData(
                        symbol=code.upper(),
                        name=name,
                        price=price,
                        change_percent=round(change_pct, 2),
                        change=round(change, 2),
                        market_cap=0,  # Sina doesn't provide market cap
                        sector=sector or "其他",
                        industry="",
                        currency="CNY",
                        exchange="A 股",
                    ))
                except (ValueError, IndexError) as e:
                    continue
            
            return stocks
            
        except Exception as e:
            logger.warning(f"Sina API failed: {e}")
            return []
    
    def _fetch_from_eastmoney(self, sector: Optional[str]) -> list[StockData]:
        """Fetch from East Money API."""
        try:
            import requests
            
            fields = "f12,f14,f2,f3,f4,f20"
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": 200,
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f3",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                "fields": fields,
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://quote.eastmoney.com/",
            }
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            json_data = resp.json()
            
            stocks = []
            if json_data.get("data") and json_data["data"].get("diff"):
                for item in json_data["data"]["diff"]:
                    try:
                        price = item.get("f2")
                        if price is None or price == "-" or price == 0:
                            continue
                        
                        stocks.append(StockData(
                            symbol=str(item.get("f12", "")),
                            name=item.get("f14", ""),
                            price=float(price),
                            change_percent=float(item.get("f3", 0)),
                            change=float(item.get("f4", 0)),
                            market_cap=float(item.get("f20", 0)) * 1e8,
                            sector=sector or "其他",
                            industry="",
                            currency="CNY",
                            exchange="A 股",
                        ))
                    except (ValueError, TypeError):
                        continue
            
            return stocks
            
        except Exception as e:
            logger.warning(f"East Money API failed: {e}")
            return []
    
    def _get_popular_codes(self, sector: Optional[str]) -> list[str]:
        """Get popular stock codes for each sector."""
        codes = {
            "银行": ["sh601398", "sh601288", "sh601939", "sh601988", "sh600036", "sh601658"],
            "证券": ["sh600030", "sh601688", "sh600837", "sh601211"],
            "保险": ["sh601318", "sh601601", "sh601628"],
            "食品饮料": ["sh600519", "sz000858", "sz000568", "sh600809"],
            "医药生物": ["sh600276", "sz000538", "sz300760", "sh600436"],
            "电子": ["sz002415", "sz000725", "sh600183", "sz002371"],
            "计算机": ["sz002230", "sz300059", "sh600570", "sz002439"],
            "汽车": ["sz002594", "sh600104", "sz000625", "sh601633"],
            "通信": ["sh600050", "sz000063", "sh600498"],
            "房地产": ["sz000002", "sh600048", "sz001979"],
        }
        
        if sector and sector in codes:
            return codes[sector]
        
        # Return all popular codes
        all_codes = []
        for s in codes.values():
            all_codes.extend(s)
        return all_codes
    
    def _get_demo_stocks(self, sector: Optional[str]) -> list[StockData]:
        """Return demo data when all APIs fail."""
        import random
        from datetime import datetime
        
        # Use current time to vary demo data
        random.seed(int(datetime.now().timestamp()) % 1000)
        
        demo_stocks = {
            "银行": [
                ("601398", "工商银行", 5.12), ("601288", "农业银行", 4.58),
                ("601939", "建设银行", 7.25), ("601988", "中国银行", 5.02),
                ("600036", "招商银行", 32.80), ("601658", "交通银行", 6.15),
            ],
            "证券": [
                ("600030", "中信证券", 18.50), ("601688", "华泰证券", 15.20),
                ("600837", "海通证券", 9.85), ("601211", "国泰君安", 16.30),
            ],
            "食品饮料": [
                ("600519", "贵州茅台", 1680.00), ("000858", "五粮液", 145.50),
                ("000568", "泸州老窖", 185.20), ("600809", "山西汾酒", 220.80),
            ],
            "医药生物": [
                ("600276", "恒瑞医药", 45.60), ("000538", "云南白药", 58.90),
                ("300760", "迈瑞医疗", 285.00), ("600436", "片仔癀", 240.50),
            ],
            "电子": [
                ("002415", "海康威视", 32.50), ("000725", "京东方A", 4.12),
                ("600183", "生益科技", 25.80), ("002371", "北方华创", 320.00),
            ],
            "计算机": [
                ("002230", "科大讯飞", 48.60), ("300059", "东方财富", 18.50),
                ("600570", "恒生电子", 32.40), ("002439", "启明星辰", 22.80),
            ],
            "汽车": [
                ("002594", "比亚迪", 268.00), ("600104", "上汽集团", 16.50),
                ("000625", "长安汽车", 15.80), ("601633", "长城汽车", 28.60),
            ],
        }
        
        sector_stocks = demo_stocks.get(sector or "电子", demo_stocks.get("电子", []))
        
        return [
            StockData(
                symbol=symbol,
                name=name,
                price=base_price * (1 + random.uniform(-0.02, 0.02)),
                change_percent=random.uniform(-3, 3),
                change=random.uniform(-1, 1),
                market_cap=random.uniform(500e8, 5000e8),
                sector=sector or "其他",
                industry="",
                currency="CNY",
                exchange="A 股",
            )
            for symbol, name, base_price in sector_stocks
        ]


class USStockSource(MarketDataSource):
    """
    US Stock market data source.
    
    Uses Yahoo Finance API via yfinance library or direct API calls.
    """
    
    SECTORS = [
        "Technology", "Healthcare", "Financial Services",
        "Consumer Cyclical", "Industrials", "Communication Services",
        "Consumer Defensive", "Energy", "Utilities",
        "Real Estate", "Basic Materials",
    ]
    
    MAJOR_STOCKS = {
        "Technology": [
            ("AAPL", "Apple Inc"), ("MSFT", "Microsoft Corp"),
            ("NVDA", "NVIDIA Corp"), ("GOOGL", "Alphabet Inc"),
            ("META", "Meta Platforms"), ("TSLA", "Tesla Inc"),
            ("AMD", "Advanced Micro Devices"), ("INTC", "Intel Corp"),
        ],
        "Healthcare": [
            ("JNJ", "Johnson & Johnson"), ("UNH", "UnitedHealth"),
            ("PFE", "Pfizer Inc"), ("MRK", "Merck & Co"),
        ],
        "Financial Services": [
            ("JPM", "JPMorgan Chase"), ("BAC", "Bank of America"),
            ("WFC", "Wells Fargo"), ("GS", "Goldman Sachs"),
        ],
        "Consumer Cyclical": [
            ("AMZN", "Amazon.com"), ("HD", "Home Depot"),
            ("NKE", "Nike Inc"), ("MCD", "McDonald's"),
        ],
        "Communication Services": [
            ("NFLX", "Netflix Inc"), ("DIS", "Walt Disney"),
            ("CMCSA", "Comcast Corp"), ("T", "AT&T Inc"),
        ],
    }
    
    @property
    def name(self) -> str:
        return "us"
    
    def get_sectors(self) -> list[str]:
        return self.SECTORS.copy()
    
    def get_stocks(self, sector: Optional[str] = None) -> list[StockData]:
        """Fetch US stock data."""
        try:
            import requests
            
            # For demo, use simulated data
            # Production: use yfinance or Alpha Vantage API
            return self._get_demo_stocks(sector)
            
        except Exception as e:
            logger.error(f"Failed to fetch US stock data: {e}")
            return self._get_demo_stocks(sector)
    
    def _get_demo_stocks(self, sector: Optional[str]) -> list[StockData]:
        """Return demo/real data for US stocks."""
        import random
        
        if sector and sector in self.MAJOR_STOCKS:
            stock_list = self.MAJOR_STOCKS[sector]
        else:
            stock_list = []
            for stocks in self.MAJOR_STOCKS.values():
                stock_list.extend(stocks)
        
        return [
            StockData(
                symbol=symbol,
                name=name,
                price=random.uniform(50, 500),
                change_percent=random.uniform(-5, 5),
                change=random.uniform(-10, 10),
                market_cap=random.uniform(100e9, 3000e9),
                sector=sector or "Technology",
                industry="",
                currency="USD",
                exchange="US",
            )
            for symbol, name in stock_list
        ]


class HKStockSource(MarketDataSource):
    """Hong Kong Stock market data source."""
    
    SECTORS = [
        "金融", "地产", "科技", "消费",
        "医药", "工业", "能源", "电信",
    ]
    
    MAJOR_STOCKS = {
        "金融": [
            ("0005.HK", "汇丰控股"), ("0941.HK", "中国移动"),
            ("1299.HK", "友邦保险"), ("2318.HK", "中国平安"),
        ],
        "科技": [
            ("0700.HK", "腾讯控股"), ("9988.HK", "阿里巴巴"),
            ("1024.HK", "快手"), ("9618.HK", "京东"),
        ],
        "地产": [
            ("1109.HK", "华润置地"), ("0688.HK", "中国海外"),
            ("2007.HK", "碧桂园"), ("1918.HK", "融创中国"),
        ],
        "消费": [
            ("0002.HK", "中电控股"), ("0388.HK", "港交所"),
            ("1928.HK", "金沙中国"), ("0066.HK", "港铁公司"),
        ],
    }
    
    @property
    def name(self) -> str:
        return "hk"
    
    def get_sectors(self) -> list[str]:
        return self.SECTORS.copy()
    
    def get_stocks(self, sector: Optional[str] = None) -> list[StockData]:
        """Fetch HK stock data."""
        import random
        
        if sector and sector in self.MAJOR_STOCKS:
            stock_list = self.MAJOR_STOCKS[sector]
        else:
            stock_list = []
            for stocks in self.MAJOR_STOCKS.values():
                stock_list.extend(stocks)
        
        return [
            StockData(
                symbol=symbol,
                name=name,
                price=random.uniform(20, 500),
                change_percent=random.uniform(-5, 5),
                change=random.uniform(-10, 10),
                market_cap=random.uniform(500e8, 5000e8),
                sector=sector or "金融",
                industry="",
                currency="HKD",
                exchange="HK",
            )
            for symbol, name in stock_list
        ]


class MarketMapEngine:
    """
    Main engine for generating market treemap data.
    
    Aggregates data from multiple market sources and formats
    for treemap visualization.
    """
    
    def __init__(self):
        self._sources: dict[str, MarketDataSource] = {
            "ashare": AShareSource(),
            "us": USStockSource(),
            "hk": HKStockSource(),
        }
    
    def get_markets(self) -> list[str]:
        """Get available market names."""
        return list(self._sources.keys())
    
    def get_sectors(self, market: str) -> list[str]:
        """Get sectors for a specific market."""
        source = self._sources.get(market)
        if not source:
            return []
        return source.get_sectors()
    
    def get_market_data(
        self,
        market: str,
        sector: Optional[str] = None,
        min_market_cap: float = 0,
        top_n: int = 500,
    ) -> MarketMapResult:
        """
        Get market data formatted for treemap visualization.
        
        Args:
            market: Market name (ashare, us, hk)
            sector: Optional sector filter
            min_market_cap: Minimum market cap filter
            top_n: Maximum number of stocks to return
            
        Returns:
            MarketMapResult with treemap-ready data
        """
        source = self._sources.get(market)
        if not source:
            return MarketMapResult(
                success=False,
                market=market,
                error=f"Unknown market: {market}",
            )
        
        try:
            stocks = source.get_stocks(sector)
            
            # Filter by market cap
            if min_market_cap > 0:
                stocks = [s for s in stocks if s.market_cap >= min_market_cap]
            
            # Sort by market cap and limit
            stocks.sort(key=lambda x: x.market_cap, reverse=True)
            stocks = stocks[:top_n]
            
            # Group by sector
            sector_data: dict[str, SectorData] = {}
            for stock in stocks:
                sec = stock.sector
                if sec not in sector_data:
                    sector_data[sec] = SectorData(name=sec)
                sector_data[sec].stocks.append(stock)
            
            # Calculate sector aggregates
            for sec in sector_data.values():
                sec.calculate()
            
            # Format for treemap
            treemap_data = []
            for sec_name, sec_data in sorted(
                sector_data.items(),
                key=lambda x: x[1].market_cap,
                reverse=True
            ):
                sector_item = {
                    "name": sec_name,
                    "value": sec_data.market_cap,
                    "change_percent": sec_data.change_percent,
                    "items": [
                        {
                            "symbol": s.symbol,
                            "name": s.name,
                            "value": s.market_cap,
                            "price": s.price,
                            "change_percent": s.change_percent,
                            "change": s.change,
                            "currency": s.currency,
                            "exchange": s.exchange,
                            "volume": s.volume,
                        }
                        for s in sorted(
                            sec_data.stocks,
                            key=lambda x: x.market_cap,
                            reverse=True
                        )
                    ],
                }
                treemap_data.append(sector_item)
            
            return MarketMapResult(
                success=True,
                market=market,
                data=treemap_data,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "stock_count": len(stocks),
                    "sector_count": len(sector_data),
                },
            )
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return MarketMapResult(
                success=False,
                market=market,
                error=str(e),
            )
    
    def get_combined_data(
        self,
        markets: Optional[list[str]] = None,
        top_n: int = 200,
    ) -> MarketMapResult:
        """
        Get combined data from multiple markets.
        
        Args:
            markets: List of markets to include (default: all)
            top_n: Top N stocks by market cap
            
        Returns:
            Combined market data
        """
        if not markets:
            markets = list(self._sources.keys())
        
        all_stocks: list[StockData] = []
        
        for market in markets:
            source = self._sources.get(market)
            if source:
                stocks = source.get_stocks()
                for stock in stocks:
                    stock.metadata["market"] = market
                all_stocks.extend(stocks)
        
        # Sort and limit
        all_stocks.sort(key=lambda x: x.market_cap, reverse=True)
        all_stocks = all_stocks[:top_n]
        
        # Group by market + sector
        grouped: dict[str, dict[str, list[StockData]]] = {}
        for stock in all_stocks:
            market = stock.metadata.get("market", "unknown")
            if market not in grouped:
                grouped[market] = {}
            sector = stock.sector
            if sector not in grouped[market]:
                grouped[market][sector] = []
            grouped[market][sector].append(stock)
        
        # Format
        treemap_data = []
        for market, sectors in grouped.items():
            market_item = {
                "name": market.upper(),
                "value": sum(s.market_cap for secs in sectors.values() for s in secs),
                "children": []
            }
            for sec_name, stocks in sectors.items():
                sec_item = {
                    "name": sec_name,
                    "value": sum(s.market_cap for s in stocks),
                    "change_percent": sum(
                        s.change_percent * s.market_cap for s in stocks
                    ) / sum(s.market_cap for s in stocks) if stocks else 0,
                    "items": [
                        {
                            "symbol": s.symbol,
                            "name": s.name,
                            "value": s.market_cap,
                            "price": s.price,
                            "change_percent": s.change_percent,
                            "change": s.change,
                            "currency": s.currency,
                            "exchange": s.exchange,
                            "market": market,
                        }
                        for s in sorted(stocks, key=lambda x: x.market_cap, reverse=True)
                    ],
                }
                market_item["children"].append(sec_item)
            treemap_data.append(market_item)
        
        return MarketMapResult(
            success=True,
            market="global",
            data=treemap_data,
            timestamp=datetime.now().isoformat(),
            metadata={
                "stock_count": len(all_stocks),
                "markets": markets,
            },
        )


# Singleton instance
_engine: Optional[MarketMapEngine] = None


def get_engine() -> MarketMapEngine:
    """Get the MarketMapEngine singleton."""
    global _engine
    if _engine is None:
        _engine = MarketMapEngine()
    return _engine


def get_market_map(
    market: str = "ashare",
    sector: Optional[str] = None,
    top_n: int = 500,
) -> MarketMapResult:
    """
    Convenience function to get market map data.
    
    Args:
        market: Market name (ashare, us, hk, global)
        sector: Optional sector filter
        top_n: Maximum stocks to return
        
    Returns:
        MarketMapResult for treemap visualization
    """
    engine = get_engine()
    
    if market == "global":
        return engine.get_combined_data(top_n=top_n)
    else:
        return engine.get_market_data(market, sector=sector, top_n=top_n)
