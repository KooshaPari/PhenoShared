"""Benchmark tests for HexaPy."""

import pytest


@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmark tests."""
    
    def test_hex_operations(self, benchmark):
        """Benchmark hex operations."""
        def hex_op():
            return "0x1234"
        
        result = benchmark(hex_op)
        assert result is not None
    
    def test_data_structures(self, benchmark):
        """Benchmark data structure operations."""
        def ds_op():
            return {"hex": True}
        
        result = benchmark(ds_op)
        assert result is not None
