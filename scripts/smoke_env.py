import os, importlib.util
from importlib.metadata import version, PackageNotFoundError
from dotenv import load_dotenv
load_dotenv("config/.env")

def mask(v): 
    if not v: return "(EMPTY)"
    return v[:6] + "..." if len(v) > 6 else "(CHECK)"

keys = ["OPENAI_API_KEY","ANTHROPIC_API_KEY","GEMINI_API_KEY"]
print("🔑 KEY STATUS")
for k in keys:
    v = os.getenv(k, "")
    print(f" - {k}: { 'OK' if v else 'EMPTY' }  {mask(v)}")

print("\n📦 PYTHON CLIENTS")
packages = [("openai","openai"), ("anthropic","anthropic"), ("google-generativeai","google.generativeai")]
for dist, mod in packages:
    spec = importlib.util.find_spec(mod)
    if spec is None:
        print(f" - {dist}: NOT INSTALLED")
    else:
        try: ver = version(dist)
        except PackageNotFoundError: ver = "unknown"
        print(f" - {dist}: INSTALLED v{ver}")

print("\n✅ If clients are INSTALLED, you're ready. Keys can be added/changed anytime.")
