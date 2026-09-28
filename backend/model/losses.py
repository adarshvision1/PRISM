"""CurbNet ACE: gamma_i=gamma_a+s(1-eta_i), omega_i=1/log(delta+eta_i)."""
import torch
def ace_lovasz(logits,target,gamma_a=2.,scale=2.,delta=1.02,alpha=1.):
    values=logits.transpose(1,2).reshape(-1,4).float(); labels=target.reshape(-1)
    mask=labels!=255; values=values[mask]; labels=labels[mask]
    if not len(labels): return logits.sum()*0
    probs=values.softmax(-1); pt=probs.gather(1,labels[:,None]).squeeze(1).clamp(1e-7,1-1e-7)
    freq=torch.bincount(labels,minlength=4).float()/len(labels)
    gamma=gamma_a+scale*(1-freq); weight=1/torch.log(delta+freq)
    ace=(-alpha*weight[labels]*(1-pt)**gamma[labels]*pt.log()).mean(); terms=[]
    for c in range(4):
        fg=(labels==c).float()
        if fg.sum()==0: continue
        errors=(fg-probs[:,c]).abs(); errors,perm=torch.sort(errors,descending=True); fg=fg[perm]
        total=fg.sum(); intersection=total-fg.cumsum(0); union=total+(1-fg).cumsum(0)
        gradient=1-intersection/union; gradient=torch.cat([gradient[:1],gradient[1:]-gradient[:-1]])
        terms.append(torch.dot(errors,gradient))
    return ace+torch.stack(terms).mean()
