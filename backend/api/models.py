"""Model selection and deployment endpoints."""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import FileResponse
from backend.application.model_service import catalog, describe
from backend.model.registry import get_spec

router = APIRouter(prefix='/api/models', tags=['Models'])


@router.get('')
def list_models():
    return catalog()


@router.get('/comparison')
def comparison_status(request: Request):
    return request.app.state.comparisons.get()


@router.post('/comparison')
def start_comparison(request: Request, frames: int = Query(default=16, ge=2, le=512)):
    try:return request.app.state.comparisons.start(frames)
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc


@router.get('/{architecture}/download')
def download(architecture: str):
    try:
        status = describe(architecture)
        spec = get_spec(architecture)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    if not status['download_ready']:
        raise HTTPException(409, 'Train and export this model first. Downloads must match the selected best checkpoint.')
    return FileResponse(spec.bundle, filename=f'PRISM-{architecture}-edge.zip', media_type='application/zip')
