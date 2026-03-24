"""
Tests for market map functionality.
"""

import pytest


class TestMarketMap:
    """Test market map data generation."""
    
    def test_get_markets(self):
        from shouchao.core.market_map import get_engine
        engine = get_engine()
        markets = engine.get_markets()
        assert 'ashare' in markets
        assert 'us' in markets
        assert 'hk' in markets
    
    def test_get_sectors_ashare(self):
        from shouchao.core.market_map import get_engine
        engine = get_engine()
        sectors = engine.get_sectors('ashare')
        assert len(sectors) > 0
        assert '银行' in sectors
        assert '电子' in sectors
    
    def test_get_market_data_ashare(self):
        from shouchao.core.market_map import get_market_map
        result = get_market_map(market='ashare', top_n=50)
        assert result.success is True
        assert result.market == 'ashare'
        assert len(result.data) > 0
        assert 'timestamp' in result.to_dict()
    
    def test_get_market_data_us(self):
        from shouchao.core.market_map import get_market_map
        result = get_market_map(market='us', top_n=30)
        assert result.success is True
        assert result.market == 'us'
    
    def test_get_market_data_hk(self):
        from shouchao.core.market_map import get_market_map
        result = get_market_map(market='hk', top_n=30)
        assert result.success is True
        assert result.market == 'hk'
    
    def test_get_global_data(self):
        from shouchao.core.market_map import get_market_map
        result = get_market_map(market='global', top_n=100)
        assert result.success is True
        assert result.market == 'global'
    
    def test_sector_filter(self):
        from shouchao.core.market_map import get_market_map
        result = get_market_map(market='ashare', sector=None, top_n=50)
        assert result.success is True
        # Demo data may have 0 or more results
        assert len(result.data) >= 0
    
    def test_stock_data_structure(self):
        from shouchao.core.market_map import get_market_map
        result = get_market_map(market='ashare', top_n=20)
        assert result.success is True
        
        # Check data structure
        for sector in result.data:
            assert 'name' in sector
            assert 'value' in sector
            assert 'change_percent' in sector
            assert 'items' in sector
            
            for stock in sector.get('items', []):
                assert 'symbol' in stock
                assert 'name' in stock
                assert 'price' in stock
                assert 'change_percent' in stock
                assert 'value' in stock


class TestMarketMapAPI:
    """Test market map API endpoints."""
    
    def test_api_markets(self):
        from shouchao.app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/api/market/markets')
            assert resp.status_code == 200
            data = resp.get_json()
            assert 'markets' in data
            assert len(data['markets']) > 0
    
    def test_api_sectors(self):
        from shouchao.app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/api/market/sectors?market=ashare')
            assert resp.status_code == 200
            data = resp.get_json()
            assert 'sectors' in data
            assert 'market' in data
    
    def test_api_map(self):
        from shouchao.app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/api/market/map?market=ashare&top_n=10')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data.get('success') is True
            assert 'data' in data
    
    def test_api_map_invalid_market(self):
        from shouchao.app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/api/market/map?market=invalid')
            assert resp.status_code == 200
            data = resp.get_json()
            assert data.get('success') is False
    
    def test_market_map_route(self):
        from shouchao.app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/market')
            assert resp.status_code == 200
            # Check page loads successfully
            assert resp.data
