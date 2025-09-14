import os
from dotenv import load_dotenv
from transformers import pipeline

# Load .env file
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
HF_TOKEN = ""


import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# ------------------- Load credentials -------------------
load_dotenv()

NEO4J_URI = "neo4j+ssc://29b1ed5d.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "4XE9segNmzkPSutRz9-KETa6AIvx4oGc3J_Zn-MfUC8"
HF_TOKEN = os.getenv("HF_TOKEN")

HF_MODEL = "distilgpt2"

# ------------------- Neo4j connection -------------------
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def run_cypher(query, params=None):
    params = params or {}
    with driver.session() as session:
        result = session.run(query, params)
        return [dict(r) for r in result]

# ------------------- Retrieval helpers -------------------
def get_region_meta(region_code):
    q = """
    MATCH (r:Region {code:$code})
    OPTIONAL MATCH (r)<-[:MEASURED_AT]-(m:RainfallMetric)
    OPTIONAL MATCH (r)<-[:MEASURED_AT]-(v:VegetationMetric)
    OPTIONAL MATCH (r)<-[:APPLIES_TO]-(a:Advisory)
    RETURN r.name AS region,
           collect(DISTINCT m.total) AS rainfalls,
           collect(DISTINCT v.value) AS ndvi_values,
           collect(DISTINCT a.title) AS advisories
    """
    res = run_cypher(q, {"code": region_code})
    return res[0] if res else {}

def get_latest_ndvi(region_code, period_key=None):
    if period_key:
        q = """
        MATCH (r:Region {code:$code})<-[:MEASURED_AT]-(v:VegetationMetric)-[:DURING]->(tp:TimePeriod {key:$p})
        OPTIONAL MATCH (v)-[:DERIVED_FROM]->(ds:DataSource)
        RETURN v.metric AS metric, v.agg AS agg, v.value AS value, v.date AS date, ds.name AS source
        ORDER BY v.date DESC
        """
        return run_cypher(q, {"code": region_code, "p": period_key})
    else:
        q = """
        MATCH (r:Region {code:$code})<-[:MEASURED_AT]-(v:VegetationMetric)
        OPTIONAL MATCH (v)-[:DERIVED_FROM]->(ds:DataSource)
        OPTIONAL MATCH (v)-[:DURING]->(tp:TimePeriod)
        RETURN v.metric AS metric, v.agg AS agg, v.value AS value, v.date AS date, tp.key AS periodKey, ds.name AS source
        ORDER BY v.date DESC LIMIT 1
        """
        return run_cypher(q, {"code": region_code})

def get_latest_rain(region_code, period_key=None):
    if period_key:
        q = """
        MATCH (r:Region {code:$code})<-[:MEASURED_AT]-(rf:RainfallMetric)-[:DURING]->(tp:TimePeriod {key:$p})
        OPTIONAL MATCH (rf)-[:DERIVED_FROM]->(ds:DataSource)
        RETURN rf.window AS window, rf.total AS total, rf.normal AS normal, rf.anomaly AS anomaly, rf.startDate AS startDate, rf.endDate AS endDate, ds.name AS source
        ORDER BY rf.startDate DESC
        """
        return run_cypher(q, {"code": region_code, "p": period_key})
    else:
        q = """
        MATCH (r:Region {code:$code})<-[:MEASURED_AT]-(rf:RainfallMetric)
        OPTIONAL MATCH (rf)-[:DERIVED_FROM]->(ds:DataSource)
        OPTIONAL MATCH (rf)-[:DURING]->(tp:TimePeriod)
        RETURN rf.window AS window, rf.total AS total, rf.normal AS normal, rf.anomaly AS anomaly, tp.key AS periodKey, rf.startDate AS startDate, rf.endDate AS endDate, ds.name AS source
        ORDER BY rf.startDate DESC LIMIT 1
        """
        return run_cypher(q, {"code": region_code})

def get_advisories(region_code):
    q = """
    MATCH (r:Region {code:$code})<-[:APPLIES_TO]-(adv:Advisory)-[:ABOUT_CROP]->(c:Crop)
    RETURN adv.title AS title, adv.text AS text, adv.date AS date, c.name AS crop
    ORDER BY adv.date DESC
    """
    return run_cypher(q, {"code": region_code})

# ------------------- Build context -------------------
def build_context(region_code, period_key=None):
    meta = get_region_meta(region_code)
    ndvi = get_latest_ndvi(region_code, period_key)
    rain = get_latest_rain(region_code, period_key)
    advs = get_advisories(region_code)

    parts = []
    parts.append(f"Region: {meta.get('region','Unknown')} (code={region_code})")
    soils = meta.get('soils') or []
    crops = meta.get('crops') or []
    if soils:
        parts.append("Soils: " + ", ".join(soils))
    if crops:
        parts.append("Common crops: " + ", ".join(crops))

    if ndvi:
        for r in ndvi:
            parts.append(f"NDVI: {r.get('value')} ({r.get('agg')}, {r.get('date')}, source: {r.get('source')})")
    if rain:
        for r in rain:
            parts.append(f"Rainfall: {r.get('total')} mm (normal: {r.get('normal')} mm, anomaly: {r.get('anomaly')} mm, period: {r.get('periodKey')}, source: {r.get('source')})")
    if advs:
        for a in advs:
            parts.append(f"Advisory: {a.get('title')} (crop: {a.get('crop')}) - {a.get('text')}")

    context = "\n".join(parts)
    return context




# ------------------- Local Hugging Face Model -------------------
HF_MODEL = "google/flan-t5-base"
generator = pipeline("text2text-generation", model=HF_MODEL)

PROMPT_TEMPLATE = """You are SatSakha, a GeoAI assistant.
Use ONLY the facts below to answer the user's question. Do NOT invent facts.

Facts:
{facts}

User question: {question}

Answer briefly and clearly. If data is insufficient, say so and suggest what data would help.
"""

def answer_question(question, region_code="IN-MH-WRD", period_key=None):
    facts = build_context(region_code, period_key)
    prompt = PROMPT_TEMPLATE.format(facts=facts, question=question)

    response = generator(prompt, max_new_tokens=200)
    return response[0]["generated_text"]





# ------------------- CLI demo -------------------


if __name__ == "__main__":
    print("SatSakha Demo (Neo4j + Local Hugging Face Model)")

    # Quick test without typing
    test_q = "Crop for Wardha in January"
    print(f"\n[Test Input] {test_q}")
    print("--- SATSAKHA ANSWER ---")
    print(answer_question(test_q, region_code="IN-MH-WRD"))

    # Then go into interactive loop
    while True:
        q = input("\nEnter question (or 'quit'): ").strip()
        if q.lower() in ("quit", "exit"): break
        ans = answer_question(q, region_code="IN-MH-WRD")
        print("\n--- SATSAKHA ANSWER ---")
        print(ans)