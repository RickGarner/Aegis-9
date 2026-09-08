"""Fail-closed local process resource budgets."""
import psutil

class ResourceBudgetError(RuntimeError): pass

class ResourceGovernor:
    def __init__(self, *, max_memory_mb: int, max_cpu_percent: float, max_children: int, process=None) -> None:
        self.max_memory_mb=max(128,min(max_memory_mb,32768)); self.max_cpu_percent=max(10,min(max_cpu_percent,100)); self.max_children=max(1,min(max_children,100)); self.process=process or psutil.Process()
    def check(self) -> dict:
        memory_mb=self.process.memory_info().rss/(1024*1024); cpu=float(self.process.cpu_percent(interval=None)); children=len(self.process.children(recursive=True))
        if memory_mb > self.max_memory_mb: raise ResourceBudgetError("A.E.G.I.S.-9 memory budget is exceeded.")
        if cpu > self.max_cpu_percent: raise ResourceBudgetError("A.E.G.I.S.-9 CPU budget is exceeded.")
        if children >= self.max_children: raise ResourceBudgetError("A.E.G.I.S.-9 child-process budget is reached.")
        return {"memoryMb": round(memory_mb,2), "cpuPercent": cpu, "children": children}
