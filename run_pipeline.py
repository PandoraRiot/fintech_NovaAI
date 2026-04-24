"""
run_pipeline.py — Orquestador del pipeline completo Bronze → Silver → Gold
Ejecuta en ~0.5 segundos en local.
"""
import time
from pipeline.bronze  import run_bronze
from pipeline.silver  import run_silver
from pipeline.gold    import run_gold

def run_full_pipeline():
    t0 = time.time()
    print("\n🚀 Iniciando pipeline Medallion...\n")
    bronze = run_bronze()
    silver = run_silver(bronze)
    gold   = run_gold(silver)
    elapsed = time.time() - t0
    print(f"\n✅ Pipeline completo en {elapsed:.2f}s")
    print(f"   Bronze: {len(bronze):,} eventos")
    print(f"   Silver: {len(silver):,} eventos enriquecidos")
    print(f"   Gold  : {len(gold):,} usuarios — {len(gold.columns)} features\n")
    return bronze, silver, gold

if __name__ == "__main__":
    run_full_pipeline()
