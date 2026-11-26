"""Model registry: lazy-load, run, unload, report memory. Safe to call from several threads."""
import gc
import threading
import time

import torch


class ModelRegistry:
    def __init__(self, device: str):
        self.device = device
        self._modules = {}  # name -> module with load() and predict()
        self._loaded = {}   # name -> bundle
        self._locks = {}    # name -> lock: each model serves one request at a time

    def register(self, name: str, module):
        self._modules[name] = module
        self._locks[name] = threading.Lock()

    def _load_locked(self, name: str):
        if name not in self._loaded:
            print(f"Loading {name} on {self.device}...")
            self._loaded[name] = self._modules[name].load(self.device)
            print(f"Loaded {name}.")
        return self._loaded[name]

    def load(self, name: str):
        with self._locks[name]:
            self._load_locked(name)

    def run(self, name: str, pil_image, question: str = None) -> dict:
        """Run one model. latency_ms covers inference only, not lock waiting or loading."""
        with self._locks[name]:
            bundle = self._load_locked(name)
            t0 = time.perf_counter()
            result = self._modules[name].predict(bundle, pil_image, self.device, question=question)
            result["latency_ms"] = (time.perf_counter() - t0) * 1000
        return result

    def unload(self, name: str):
        with self._locks[name]:  # wait for a running request before removing
            if self._loaded.pop(name, None) is not None:
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    def list(self):
        rows = []
        for name in self._modules:
            bundle = self._loaded.get(name)
            mem_mb = 0.0
            if bundle:
                for obj in bundle.values():
                    if hasattr(obj, "parameters"):
                        mem_mb += sum(p.numel() * p.element_size() for p in obj.parameters()) / 1e6
            rows.append({
                "name": name,
                "loaded": bundle is not None,
                "device": self.device if bundle else None,
                "approx_memory_mb": round(mem_mb, 1),
            })
        return rows
