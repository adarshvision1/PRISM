"""Small checks for model selection, trainability and artifact isolation."""
import pytest
import torch
from fastapi.testclient import TestClient
from backend.model.registry import build_model, get_spec, checkpoint_architecture
from backend.model.training_lock import training_lock
from backend.api.server import app


def test_pointnext_forward_backward_and_shapes():
    torch.set_num_threads(4)
    model=build_model('pointnext_s')
    x=torch.randn(2,6,1024)
    logits=model(x)
    assert logits.shape==(2,4,1024) and torch.isfinite(logits).all()
    logits.square().mean().backward()
    assert model.encoder[0].skip.weight.grad is not None
    model.eval()
    with torch.inference_mode():
        assert model(torch.randn(1,6,4096)).shape==(1,4,4096)
        traced=torch.jit.trace(model,torch.randn(1,6,1024),check_trace=False)
        sample=torch.randn(2,6,1024)
        assert torch.allclose(model(sample),traced(sample),rtol=1e-4,atol=1e-5)


def test_registry_isolates_artifacts_and_preserves_old_checkpoints():
    assert get_spec('pointnext_s').checkpoint!=get_spec('pointnet2').checkpoint
    assert get_spec('pointnext_s').bundle!=get_spec('pointnet2').bundle
    assert checkpoint_architecture({})=='pointnet2'
    with pytest.raises(ValueError):build_model('../arbitrary')


def test_model_catalog_and_unavailable_model_fail_clearly():
    with TestClient(app) as client:
        models=client.get('/api/models').json()['models']
        assert {m['id'] for m in models}=={'pointnet2','pointnext_s'}
        assert client.post('/api/sample?architecture=unknown').status_code==409
        assert client.get('/api/models/unknown/download').status_code==404
        assert client.get('/api/models/comparison').json()['status']=='idle'
        assert client.post('/api/models/comparison?frames=0').status_code==422
        pending=next(m for m in models if m['id']=='pointnext_s')
        if not pending['ready']:
            assert client.post('/api/sample?architecture=pointnext_s').status_code==409
            assert client.get('/api/models/pointnext_s/download').status_code==409
            assert client.post('/api/models/comparison').status_code==409


def test_training_lock_rejects_duplicate():
    with training_lock():
        with pytest.raises(RuntimeError):
            with training_lock():pass
