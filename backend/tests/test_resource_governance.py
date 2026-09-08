import pytest
from app.resource_governance import ResourceBudgetError, ResourceGovernor

class FakeProcess:
    def memory_info(self): return type("Memory",(),{"rss":300*1024*1024})()
    def cpu_percent(self,interval=None): return 20
    def children(self,recursive=True): return []

def test_resource_governor_rejects_excess_memory():
    with pytest.raises(ResourceBudgetError,match="memory"):
        ResourceGovernor(max_memory_mb=128,max_cpu_percent=90,max_children=2,process=FakeProcess()).check()
