
APP_VERSION = "7.1"
import os, io, re, numpy as np, pandas as pd, streamlit as st

try:
    from invoice_parser import parse_invoice_bytes, parse_image_bytes
    PARSER_OK = True
except Exception:
    PARSER_OK = False

st.set_page_config(page_title="PVP La Terraza", page_icon=":tropical_drink:", layout="wide")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
st.markdown('''<style>
@import url("https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;800&display=swap");
:root{--bg:#fffaf2;--ink:#222;--muted:#667085;--line:#eadfb8;--gold:#d4af37;}
html,body,.stApp{background:var(--bg)!important;color:var(--ink);font-family:"Nunito",sans-serif}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line)}
.stTextInput>div>div>input,.stNumberInput input,textarea,.stSelectbox>div>div,.stFileUploader>div>div{background:#fffaf2!important;color:#2c2c2c!important;border:1px solid var(--gold)!important;border-radius:10px!important}
.stCameraInput{border:1px solid var(--gold)!important;border-radius:12px!important;background:#fff}
.center-row{display:flex;align-items:center;justify-content:center}
#footer-btn{background:var(--gold);color:#2b2b2b;font-weight:700;border:none;border-radius:12px;padding:12px 22px}
.header-title{text-align:center;font-weight:800;color:var(--gold);font-size:32px;margin:12px 0 8px 0}
.note{text-align:center;color:var(--muted);margin-bottom:8px}
.sep{border:none;border-top:1px solid var(--line);margin:14px 0}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="header-title">La Terraza BenalBeach</div>', unsafe_allow_html=True)
st.markdown(f'<div class="note">PVP La Terraza · v{APP_VERSION}</div>', unsafe_allow_html=True)
st.markdown('<hr class="sep">', unsafe_allow_html=True)

@st.cache_data
def _load_csv(name): 
    p=os.path.join(DATA_DIR,name); 
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()

@st.cache_data
def _load_settings():
    import yaml; p=os.path.join(DATA_DIR,"settings.yaml")
    return yaml.safe_load(open(p,"r",encoding="utf-8")) if os.path.exists(p) else {"currency_symbol":"€"}

SET=_load_settings(); currency=SET.get("currency_symbol","€")
cm=_load_csv("category_margins.csv"); ing=_load_csv("ingredient_yields.csv"); rec=_load_csv("recipes.csv"); rl=_load_csv("recipe_lines.csv"); pur=_load_csv("purchases.csv")

with st.sidebar:
    st.header("Márgenes por sección")
    cm=st.data_editor(cm, num_rows="dynamic", use_container_width=True, key="cm_editor")
    cm.to_csv(os.path.join(DATA_DIR,"category_margins.csv"), index=False, encoding="utf-8")
    st.caption("Márgenes guardados (auto).")

st.markdown("<a id='compras'></a>", unsafe_allow_html=True)
st.subheader("1) Compras (facturas)")
up=st.file_uploader("📤 Sube facturas (PDF/JPG/PNG)", type=["pdf","jpg","jpeg","png"], accept_multiple_files=True, key="uploader", label_visibility="visible")
cam=st.camera_input("📸 O toma una foto de la factura")
if cam is not None: up=list(up) if up else []; up.append(cam)

if up:
    st.markdown("### Facturas subidas")
    for f in up: st.write(f"• {getattr(f,'name','foto')} lista para procesar")

new_rows_all=[]
if up:
    for f in up:
        fname=getattr(f,"name","foto.jpg"); st.markdown(f"#### Procesar {fname}")
        iva_rate=0.10; parsed=pd.DataFrame()
        if fname.lower().endswith(".pdf") and PARSER_OK:
            try: parsed=parse_invoice_bytes(f.read())
            except Exception as e: st.warning(f"No se pudo leer automáticamente {fname}: {e}")
        else:
            if PARSER_OK:
                try: parsed=parse_image_bytes(f.getvalue())
                except Exception: pass
        col1,col2,col3=st.columns(3)
        supplier=col1.text_input("Proveedor","",key=f"supplier_{fname}")
        date=col2.text_input("Fecha (DD/MM/AAAA)","",key=f"date_{fname}")
        invoice_no=col3.text_input("Nº factura","",key=f"invoice_{fname}")
        iva_rate=st.number_input("IVA aplicado",0.0,0.30,float(iva_rate),0.01,key=f"iva_{fname}",format="%.2f")
        if not parsed.empty:
            st.caption("Líneas detectadas (edita si quieres):")
            parsed=st.data_editor(parsed, use_container_width=True, key=f"parsed_{fname}")
            if st.button(f"Guardar {len(parsed)} líneas", key=f"save_{fname}"):
                for _,r in parsed.iterrows():
                    new_rows_all.append({"date":date,"supplier":supplier,"ingredient":r["ingredient"],"qty":float(r["qty"]),"unit":r["unit"],"total_cost_gross":float(r["total_cost_gross"]),"iva_rate":iva_rate,"invoice_no":invoice_no,"notes":f"auto:{fname}"})
        else:
            st.caption("No se detectó texto. Añade manualmente una línea:")
            ingr=st.text_input("Ingrediente", key=f"ingr_{fname}")
            qty=st.number_input("Cantidad",0.0,1e9,1.0,0.1,key=f"qty_{fname}")
            unit=st.text_input("Unidad (kg, L, unit)","kg",key=f"unit_{fname}")
            total=st.number_input("Total con IVA (€)",0.0,1e9,0.0,0.1,key=f"total_{fname}")
            if st.button("Guardar línea", key=f"add_{fname}"):
                new_rows_all.append({"date":date,"supplier":supplier,"ingredient":ingr,"qty":qty,"unit":unit,"total_cost_gross":total,"iva_rate":iva_rate,"invoice_no":invoice_no,"notes":f"manual:{fname}"})

if new_rows_all:
    pur=pd.concat([pur, pd.DataFrame(new_rows_all)], ignore_index=True)
    pur.to_csv(os.path.join(DATA_DIR,"purchases.csv"), index=False, encoding="utf-8")
    st.success(f"Guardadas {len(new_rows_all)} líneas en compras.")
    st.rerun()

st.subheader("Ingredientes (mermas)")
ing=st.data_editor(ing, num_rows="dynamic", use_container_width=True, key="ing_editor")
ing.to_csv(os.path.join(DATA_DIR,"ingredient_yields.csv"), index=False, encoding="utf-8")
st.caption("Mermas guardadas.")

st.subheader("Carta")
st.dataframe(rec[["category","display_name","iva_rate"]].rename(columns={"category":"Sección","display_name":"Producto","iva_rate":"IVA"}), use_container_width=True)

def compute_cost_map(purchases, yields):
    if purchases.empty: return pd.DataFrame(columns=["ingredient","unit","unit_cost_net","usable_yield","effective_cost"])
    df=purchases.copy(); df["unit_cost_net"]=df["total_cost_gross"]/(1.0+df["iva_rate"].fillna(0.10))/df["qty"].replace(0, np.nan)
    df["_k_ing"]=df["ingredient"].astype(str).str.strip().str.lower().str.replace(r"\s+"," ", regex=True)
    df["_k_unit"]=df["unit"].astype(str).str.strip().str.lower().str.replace(r"\s+"," ", regex=True)
    y=yields.copy(); y["_k_ing"]=y["ingredient"].astype(str).str.strip().str.lower().str.replace(r"\s+"," ", regex=True); y["_k_unit"]=y["unit"].astype(str).str.strip().str.lower().str.replace(r"\s+"," ", regex=True)
    last=df.reset_index().groupby(["_k_ing","_k_unit"]).last(numeric_only=True).reset_index()
    r=last.merge(y[["_k_ing","_k_unit","usable_yield"]], on=["_k_ing","_k_unit"], how="left"); r["usable_yield"]=r["usable_yield"].fillna(1.0)
    r["effective_cost"]=r["unit_cost_net"]/r["usable_yield"].replace(0, np.nan); r["ingredient"]=r["_k_ing"]; r["unit"]=r["_k_unit"]
    return r[["ingredient","unit","unit_cost_net","usable_yield","effective_cost"]]

def compute_pvp(recipes, recipe_lines, helper, margins_df):
    cost_map={(row["ingredient"],row["unit"]):row["effective_cost"] for _,row in helper.iterrows()}
    margins={str(r["category"]):float(r["target_margin"]) for _,r in margins_df.iterrows() if pd.notna(r["target_margin"])}
    rows=[]
    for _,r in recipes.iterrows():
        item_key=r["item_key"]; iva=float(r.get("iva_rate",0.10)) if pd.notna(r.get("iva_rate",np.nan)) else 0.10; margin=margins.get(r["category"],0.70)
        item_lines=recipe_lines[recipe_lines["item_key"]==item_key]; cost_ing=0.0; missing=False
        for _,ln in item_lines.iterrows():
            k=(str(ln["ingredient"]).strip().lower(), str(ln["unit"]).strip().lower()); c=cost_map.get(k, np.nan)
            if pd.isna(c): missing=True; continue
            cost_ing+=c*float(ln["qty_per_portion"])
        price_excl=cost_ing/(1.0-margin) if cost_ing>0 else np.nan; pvp=price_excl*(1.0+iva) if pd.notna(price_excl) else np.nan
        rows.append({"Sección":r["category"],"Producto":r["display_name"],"Margen":f"{margin*100:.0f}%","IVA":f"{iva*100:.0f}%","Coste ingredientes":cost_ing,"PVP":pvp,"Faltan costes":"Sí" if missing else ""})
    return pd.DataFrame(rows)

helper=compute_cost_map(pur, ing)
st.subheader("PVP sugerido")
if helper.empty:
    st.info("Sube al menos una factura con precios para calcular PVP.")
else:
    pr=compute_pvp(rec, rl, helper, cm).sort_values(["Sección","Producto"])
    for c in ["Coste ingredientes","PVP"]:
        pr[c]=pr[c].map(lambda x: f"{x:.2f}{currency}" if pd.notna(x) else "")
    st.dataframe(pr, use_container_width=True)

st.markdown('<div class="center-row" style="margin:18px 0 8px 0;"><a href="#compras"><button id="footer-btn">📤 Subir factura</button></a></div>', unsafe_allow_html=True)
