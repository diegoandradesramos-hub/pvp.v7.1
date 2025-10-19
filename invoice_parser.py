
import io, re, numpy as np
import pdfplumber, pandas as pd
from PIL import Image

try:
    import easyocr
    _OCR_READER = easyocr.Reader(['es','en'], gpu=False)
except Exception:
    _OCR_READER = None

UNIT_RE = r"""(?:kg|kgr|kgs|g|gr|grs|l|lt|lts|ml|ud|uds|u|unidad|unidades|unit)"""
UNIT_MAP = {"ud":"unit","uds":"unit","unidad":"unit","unidades":"unit","u":"unit","unit":"unit","kg":"kg","kgr":"kg","kgs":"kg","g":"g","gr":"g","grs":"g","l":"L","lt":"L","lts":"L","ml":"ml"}
PAT1 = re.compile(r"""(?P<desc>[^0-9]{3,}?)\s+(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>"""+UNIT_RE+r""")\b.*?(?P<total>\d+(?:[.,]\d+)?)\s*€?""", re.IGNORECASE)
PAT2 = re.compile(r"""(?P<desc>[^0-9]{3,}?)\s+(?P<total>\d+(?:[.,]\d+)?)\s*€?\s+.*?(?P<qty>\d+(?:[.,]\d+)?)\s*(?P<unit>"""+UNIT_RE+r""")\b""", re.IGNORECASE)

def _to_float(x):
    x=str(x).strip().replace("€","").replace("EUR","")
    x=x.replace(".","").replace(",",".") if x.count(",")==1 and x.count(".")>1 else x.replace(",",".")
    try: return float(x)
    except: return None

def _norm_unit(u):
    u=u.strip().lower().replace(".",""); return UNIT_MAP.get(u,u)

def _to_base(qty, unit):
    if unit=="g": return qty/1000.0, "kg"
    if unit=="ml": return qty/1000.0, "L"
    return qty, unit

def _extract(text):
    rows=[]
    for raw in text.splitlines():
        line=raw.strip()
        if not line or len(line)<5: continue
        m=PAT1.search(line) or PAT2.search(line)
        if not m: continue
        desc=re.sub(r"\s+"," ", m.group("desc")).strip(" .:-")
        qty=_to_float(m.group("qty")); unit=_norm_unit(m.group("unit")); total=_to_float(m.group("total"))
        if qty is None or total is None: continue
        qty,unit=_to_base(qty,unit)
        rows.append({"ingredient":desc, "qty":qty, "unit":unit, "total_cost_gross":total})
    df=pd.DataFrame(rows)
    if df.empty: return df
    return df.groupby(["ingredient","unit"], as_index=False).agg({"qty":"sum","total_cost_gross":"sum"})

def parse_invoice_bytes(pdf_bytes: bytes) -> pd.DataFrame:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text="\n".join(page.extract_text() or "" for page in pdf.pages)
    df=_extract(text)
    if not df.empty: return df
    if _OCR_READER is not None:
        pages_text=[]
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                img = page.to_image(resolution=200).original
                result=_OCR_READER.readtext(img, detail=0, paragraph=True)
                pages_text.append("\n".join(result))
        return _extract("\n".join(pages_text))
    return pd.DataFrame(columns=["ingredient","qty","unit","total_cost_gross"])

def parse_image_bytes(img_bytes: bytes) -> pd.DataFrame:
    if _OCR_READER is None:
        return pd.DataFrame()
    try:
        from PIL import Image
        import numpy as _np
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        result = _OCR_READER.readtext(_np.array(img), detail=0, paragraph=True)
        text = "\n".join(result)
        return _extract(text)
    except Exception:
        return pd.DataFrame()

