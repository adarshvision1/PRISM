"""Queue model comparisons alongside inference jobs on the single GPU worker."""
import gc
import threading
from .model_service import require_ready
from backend.model.registry import MODELS


class ComparisonService:
    def __init__(self, manager):
        self.manager = manager
        self.lock = threading.RLock()
        self.state = {'status': 'idle'}

    def get(self):
        with self.lock:return dict(self.state)

    def start(self, frames):
        for key in MODELS:require_ready(key)
        with self.lock:
            if self.state['status'] in ('queued','running'):return dict(self.state)
            self.state={'status':'queued','frames_per_model':frames,'completed':0,'total':frames*2,'error':None}
            self.manager.pool.submit(self._run, frames)
            return dict(self.state)

    def _run(self, frames):
        from backend.eval.model_comparison import compare_models
        def progress(architecture, done, total):
            with self.lock:self.state.update(architecture=architecture,completed=done+(total if architecture=='pointnext_s' else 0),total=total*2)
        try:
            with self.lock:self.state['status']='running'
            with self.manager.lock:
                self.manager.predictor=None;gc.collect()
                compare_models(frames,progress)
            with self.lock:self.state['status']='complete'
        except Exception as exc:
            with self.lock:self.state.update(status='failed',error=str(exc))
