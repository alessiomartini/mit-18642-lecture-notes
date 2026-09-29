"""Fast build for LaTeX Workshop: recompile only the chapter just saved.

A full pass over the 500-page book takes ~70-90 s and latexmk runs 2-3 of them;
a single chapter takes a few seconds and keeps the SyncTeX file small, so
double-click (PDF -> source) stays instant. Page numbers and cross-references
to other chapters come from their .aux files in build/.

Falls back to a full latexmk build when main.tex/preamble.tex was the last file
saved, or when build/ has no .aux files yet. `python build.py full` forces it.
"""
import glob
import msvcrt
import os
import re
import shutil
import subprocess
import sys
import time

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# One build at a time: two pdflatex runs writing build/main.out together (e.g. a save
# while another build is running) interleave their writes and corrupt the file.
os.makedirs('build', exist_ok=True)
lock = open('build/.build.lock', 'w')
while True:
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        break
    except OSError:
        time.sleep(0.5)

parts = glob.glob('chapters/*.tex') + glob.glob('appendices/*.tex')
newest = max(parts + ['main.tex', 'preamble.tex'], key=os.path.getmtime)
auxes = ['main.aux'] + [p[:-4] + '.aux' for p in parts]


def complete(aux, root='build'):
    """A killed build leaves an aux truncated (often empty) but readable: LaTeX then
    silently loses every label. Complete = LaTeX got to the end of it."""
    try:
        text = open(os.path.join(root, aux), encoding='latin-1').read()
    except OSError:
        return False
    return (r'\@abspage@last' if aux == 'main.aux' else r'\@setckpt') in text


# Restore truncated aux files from the snapshot of the last complete build
for aux in auxes:
    if not complete(aux) and complete(aux, 'build/good'):
        print(f'Restored build/{aux} from snapshot (a previous build was interrupted)', flush=True)
        os.makedirs(os.path.dirname(os.path.join('build', aux)), exist_ok=True)
        shutil.copyfile(os.path.join('build/good', aux), os.path.join('build', aux))
aux_ready = all(complete(aux) for aux in auxes)
common = ['-synctex=1', '-interaction=nonstopmode', '-file-line-error']

full_cmd = ['latexmk', '-pdf', '-outdir=build', *common, 'main.tex']
if 'full' in sys.argv[1:] or newest in ('main.tex', 'preamble.tex') or not aux_ready:
    cmd = full_cmd
else:
    # ponytail: one pdflatex pass; a label added in this chapter resolves on the next save or full build
    chapter = newest[:-4].replace(os.sep, '/')
    print(f'Fast build: {chapter} only (run the "full" recipe for the whole book)', flush=True)
    cmd = ['pdflatex', *common, '-output-directory=build', '-jobname=main',
           rf'\includeonly{{{chapter}}}\input{{main}}']

code = subprocess.call(cmd)
try:
    log = open('build/main.log', encoding='latin-1').read().replace('\n', '')
except OSError:
    log = ''
# A build killed mid-write (a new save restarts it) leaves truncated or NUL-filled
# aux/out/toc files that break every later build: drop them all and rebuild the book.
if code and re.search(r'\.(aux|out|toc):\d+:', log):
    print('Corrupt auxiliary files in build/: removing them and running a full build', flush=True)
    for f in ['build/main.out', 'build/main.toc', *(os.path.join('build', a) for a in auxes)]:
        if os.path.exists(f):
            os.remove(f)
    code = subprocess.call(full_cmd)

# Keep the last whole book: fast builds overwrite build/main.pdf with one chapter only
if cmd is full_cmd and code == 0:
    try:
        shutil.copyfile('build/main.pdf', 'build/book.pdf')
    except OSError as e:  # book.pdf open in a viewer that locks it
        print(f'Could not update build/book.pdf: {e}', flush=True)

# Snapshot the aux files once they are all complete, for the restore above
if all(complete(aux) for aux in auxes):
    for aux in auxes:
        os.makedirs(os.path.dirname(os.path.join('build/good', aux)), exist_ok=True)
        shutil.copyfile(os.path.join('build', aux), os.path.join('build/good', aux))

sys.exit(code)
