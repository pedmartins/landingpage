import os, sys, datetime as dt
sys.path.insert(0, os.getcwd())
os.environ.update(WC_URL="https://x.test", WC_CK="ck", WC_CS="cs")
import wc_catalog as w
A=lambda n,v,vis=True:{"name":n,"options":v,"visible":vis}
parents=[{"id":1,"name":"PECB ISO/IEC 42001 Lead Auditor","slug":"pecb-iso-iec-42001-lead-auditor","type":"grouped","status":"publish","sku":"LW-PECB-42001-LA","menu_order":10,
 "short_description":"<p>curto</p><script>x</script>","description":"<h3>D</h3><p>t</p>","images":[{"src":"https://r2/x.png","alt":""}],
 "categories":[{"name":"Gestão de IA"}],"tags":[{"name":"PECB"}],"attributes":[A("Norma / Regulamento",["ISO/IEC 42001"]),A("Nível",["Lead Auditor"])],
 "grouped_products":[11,12,13,14]},
 {"id":2,"name":"Outro","slug":"outro","type":"grouped","status":"publish","sku":"XX-1","grouped_products":[]}]
children=[
 {"id":11,"name":"ed passada","status":"publish","sku":"LW-PECB-42001-LA-2026-11-02","external_url":"https://c/1","button_text":"Inscrever","attributes":[A("Data de início",["2026-11-02"]),A("Data de fim",["2026-11-06"]),A("Formato",["Online"])]},
 {"id":12,"name":"ed futura","status":"publish","sku":"LW-PECB-42001-LA-2027-05-17","external_url":"https://c/2","button_text":"Inscrever","attributes":[A("Data de início",["2027-05-17"]),A("Data de fim",["2027-05-21"]),A("Formato",["Online"])]},
 {"id":13,"name":"consulta","status":"publish","sku":"LW-PECB-42001-LA-CONSULTA","external_url":"https://c/#contact","button_text":"Pedir","attributes":[]},
 {"id":14,"name":"rascunho","status":"draft","sku":"LW-PECB-42001-LA-2027-11-15","external_url":"https://c/3","attributes":[A("Data de início",["2027-11-15"])]}]
calls=[]
def fake(path, params):
    calls.append(params)
    if params.get("type")=="grouped": return parents
    ids=set(map(int,params["include"].split(","))); return [c for c in children if c["id"] in ids and c["status"]==params["status"]]
w._get_all=fake
data=w.get_catalog(force=True)
assert len(data)==1, "prefixo SKU"
c=data[0]; assert [e["id"] for e in c["editions"]]==[12], c["editions"]  # passada e rascunho fora
assert c["enquiry"]["id"]==13 and c["standard"]=="ISO/IEC 42001"
assert all(p["status"]=="publish" for p in calls)
from flask import Flask, render_template_string
from formacao_bp import formacao_bp
app=Flask(__name__); app.register_blueprint(formacao_bp)
import jinja2; app.jinja_loader=jinja2.ChoiceLoader([jinja2.DictLoader({"base.html":"<html>{% block content %}{% endblock %}</html>"}), app.jinja_loader])
cl=app.test_client()
r=cl.get("/formacao/pecb-iso-iec-42001-lead-auditor"); assert r.status_code==200; h=r.data.decode()
assert "<script>" not in h and "2027-05-17" in h and "https://c/#contact" in h and "2026-11-02" not in h
assert cl.get("/formacao/nao-existe").status_code==404
assert cl.get("/formacao").status_code==200 and cl.get("/api/formacao.json").json[0]["level"]=="Lead Auditor"
print("todos os testes OK")
