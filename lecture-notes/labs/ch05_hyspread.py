"""Lab, chapter 5: the high-yield spread fitted by polynomials in time, Fourier terms and an autoregression.

Reproduces the case study of lec06_2 / lec06_3 (18.642, 2024) with the FRED series BAA10Y in
../data/fm_hyspread.dat. Run:  python labs/ch05_hyspread.py   (from lecture-notes/; --plot draws the fits)
Try the lab yourself first: this file is the reference solution.
"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
data = np.genfromtxt(os.path.join(HERE, '..', 'data', 'fm_hyspread.dat'), comments='%', skip_header=4,
                     dtype=None, encoding='utf8', names=('date', 'spread'))
y = data['spread'].astype(float)
n = len(y)
t = np.linspace(-1, 1, n)  # time rescaled to [-1, 1]: powers of calendar time are badly conditioned


def r2(X, y):
    """Least squares fit of y on the columns of X; returns R^2 and the fitted values."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit = X @ beta
    return 1 - np.sum((y - fit) ** 2) / np.sum((y - y.mean()) ** 2), fit


fits = {}
print(f'{n} daily observations, {data["date"][0]} to {data["date"][-1]}, spread {y.min()}..{y.max()} pp')
print('\nPolynomials in time (lec06_2)')
for k in range(9):
    fits[f'poly {k}'] = r2(np.vander(t, k + 1), y)
    print(f'  order {k}: R^2 = {fits[f"poly {k}"][0]:.3f}')

print('\nFourier terms, j = 1..J cycles over the sample (lec06_3)')
u = np.pi * (t + 1)  # 0 .. 2*pi over the sample
for J in range(1, 5):
    X = np.column_stack([np.ones(n)] + [f(j * u) for j in range(1, J + 1) for f in (np.sin, np.cos)])
    fits[f'fourier {J}'] = r2(X, y)
    print(f'  J = {J}: R^2 = {fits[f"fourier {J}"][0]:.3f}')

print('\nAutoregression y_t = a + b y_(t-1) (shown in class, not in the files)')
R2_ar, _ = r2(np.column_stack([np.ones(n - 1), y[:-1]]), y[1:])
b = np.linalg.lstsq(np.column_stack([np.ones(n - 1), y[:-1]]), y[1:], rcond=None)[0][1]
print(f'  b = {b:.4f}, R^2 = {R2_ar:.4f}   (class: R^2 = 0.995)')

# the lesson of the case study, as a check: persistence beats any function of calendar time
assert R2_ar > 0.99 and R2_ar > max(v[0] for v in fits.values()), 'unexpected: AR(1) should fit best'

if '--plot' in sys.argv:
    import matplotlib.pyplot as plt
    days = data['date'].astype('datetime64[D]')
    fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    for a, keys in zip(ax, (['poly 0', 'poly 1', 'poly 2', 'poly 4', 'poly 8'], ['fourier 1', 'fourier 2', 'fourier 4'])):
        a.plot(days, y, color='0.6', lw=0.8, label='spread')
        for k in keys:
            a.plot(days, fits[k][1], lw=1.4, label=k)
        a.set_ylabel('Baa - 10y (pp)')
        a.legend(fontsize=8)
    ax[0].set_title('High-yield spread: fits by functions of time')
    plt.tight_layout()
    plt.show()
