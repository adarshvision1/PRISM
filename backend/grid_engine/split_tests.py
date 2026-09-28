"""Near-purity categorical test with explicit nonzero contamination null."""
import numpy as np
from scipy.stats import chi2
def semantic_split(counts,entropy_threshold=.18,contamination=.05,alpha=.01):
    counts=np.asarray(counts,float); n=counts.sum(1); safe=np.maximum(n,1)
    p=counts/safe[:,None]; entropy=-(p*np.log(np.maximum(p,1e-15))).sum(1)/np.log(4)
    # A literal all-dominant null has expected zeros and invalid chi-square.
    # Use a documented 95% dominant/5% contamination null, fitted dominant.
    expected=np.full_like(counts,contamination/3)*n[:,None]
    dominant=counts.argmax(1);expected[np.arange(len(n)),dominant]=(1-contamination)*n
    enough=(expected>=5).all(1)
    statistic=((counts-expected)**2/np.maximum(expected,1e-12)).sum(1)
    # Pure cells must not split for being MORE pure than the null.
    contaminated=counts.max(1)<(1-contamination)*n
    return np.where(enough,contaminated & (statistic>chi2.ppf(1-alpha,3)),entropy>entropy_threshold)
