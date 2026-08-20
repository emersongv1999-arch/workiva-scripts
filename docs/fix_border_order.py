import re, shutil, subprocess, sys, os, zipfile
ORDER = ["top","left","bottom","right","between","bar"]
src = sys.argv[1]
work = "fixwork"
shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
with zipfile.ZipFile(src) as z: z.extractall(work)
p = os.path.join(work, "word", "document.xml")
s = open(p, encoding="utf-8").read()
def reorder(m):
    inner = m.group(2)
    kids = re.findall(r'<w:(?:top|left|bottom|right|between|bar)\b[^>]*/>', inner)
    if len(kids) <= 1: return m.group(0)
    key = lambda k: ORDER.index(re.match(r'<w:(\w+)', k).group(1))
    return f"<w:{m.group(1)}>" + "".join(sorted(kids, key=key)) + f"</w:{m.group(1)}>"
s2, n = re.subn(r'<w:(pBdr)>(.*?)</w:\1>', reorder, s, flags=re.S)
open(p, "w", encoding="utf-8").write(s2)
out = os.path.abspath(sys.argv[2])
if os.path.exists(out): os.remove(out)
subprocess.run(["zip","-Xrq",out,"."], cwd=work, check=True)
print(f"reordered {n} pBdr blocks -> {out}")
