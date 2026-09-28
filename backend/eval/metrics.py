import numpy as np
def confusion(truth,pred,mask=None):
    valid=truth<4
    if mask is not None:valid &= mask
    p=np.minimum(pred[valid],4)
    return np.bincount(truth[valid].astype(int)*5+p,minlength=20).reshape(4,5)
def scores(matrix):
    matrix=np.asarray(matrix);diag=np.diag(matrix[:,:4]);union=matrix.sum(1)+matrix[:,:4].sum(0)-diag
    iou=[float(diag[i]/union[i]) if union[i]>0 else None for i in range(4)]
    values=[x for x in iou if x is not None]
    precision=[float(diag[i]/matrix[:,:4].sum(0)[i]) if matrix[:,:4].sum(0)[i] else None for i in range(4)]
    recall=[float(diag[i]/matrix.sum(1)[i]) if matrix.sum(1)[i] else None for i in range(4)]
    f1=[2*p*r/(p+r) if p is not None and r is not None and p+r else (0. if p==0 or r==0 else None) for p,r in zip(precision,recall)]
    return {'iou':iou,'precision':precision,'recall':recall,'f1':f1,'accuracy':float(diag.sum()/matrix.sum()) if matrix.sum() else None,'miou':float(np.mean(values)) if values else None,'labeled_points':int(matrix.sum()),'confusion':matrix.tolist()}
