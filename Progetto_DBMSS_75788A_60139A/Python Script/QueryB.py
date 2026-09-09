import pandas as pd
from neo4j import GraphDatabase
import time

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678" 

# --- OPTION 1: DATASET SMALL (97 Days: Gennaio -> 7 Aprile) ---
#START_PREV = "2025-01-01"
#END_PREV   = "2025-03-31"
#START_CURR = "2025-04-01"
#END_CURR   = "2025-04-10"

# --- OPTION 2: DATASET MEDIUM (187 Days) & LARGE (367 Days) ---
START_PREV = "2025-01-01"
END_PREV   = "2025-03-31"
START_CURR = "2025-04-01"
END_CURR   = "2025-06-30"

class Neo4jAnalyticsQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query_4b(self):
        print(f"Esecuzione Query 4.b (Date Ottimizzate)...")
        print(f"      Baseline (Prev): {START_PREV} -> {END_PREV}")
        print(f"      Analisi  (Curr): {START_CURR} -> {END_CURR}")
        
        start_time = time.time()
        
        query = """
        // 1. MATCH sul periodo PRECEDENTE (Baseline)
        MATCH (t:Terminal)<-[:OCCURRED_AT]-(tx_prev:Transaction)
        // Convertiamo la stringa data in oggetto Date reale
        WHERE date(datetime(replace(tx_prev.date, ' ', 'T'))) >= date($start_prev) 
          AND date(datetime(replace(tx_prev.date, ' ', 'T'))) <= date($end_prev)
          
        // Calcoliamo la mediana storica per il terminale
        WITH t, percentileCont(tx_prev.amount, 0.5) as median_prev
        
        // 2. MATCH sul periodo CORRENTE (Analisi)
        MATCH (t)<-[:OCCURRED_AT]-(tx_curr:Transaction)
        WHERE date(datetime(replace(tx_curr.date, ' ', 'T'))) >= date($start_curr) 
          AND date(datetime(replace(tx_curr.date, ' ', 'T'))) <= date($end_curr)
        
        // 3. Filtro OUTLIER: Importo > 130% Della mediana storica
        AND tx_curr.amount > (1.3 * median_prev)
        
        // 4. Output
        RETURN 
            t.id as Terminal_ID,
            median_prev as Prev_Median_Amount,
            tx_curr.id as Outlier_Tx_ID,
            tx_curr.amount as Outlier_Amount,
            tx_curr.date as Tx_Date,
            "potential outlier" as Label
        ORDER BY t.id, tx_curr.amount DESC
        """
        
        parameters = {
            "start_prev": START_PREV, "end_prev": END_PREV,
            "start_curr": START_CURR, "end_curr": END_CURR
        }
        
        with self.driver.session() as session:
            result = session.run(query, parameters)
            data = [record.data() for record in result]

        elapsed = time.time() - start_time
        df = pd.DataFrame(data)
        
        print(f"Query completata in {elapsed:.2f} s")
        print(f"      Trovati {len(df)} potenziali outliers.")
        return df, elapsed

if __name__ == "__main__":
    analyzer = Neo4jAnalyticsQuery(DB_URI, "neo4j", DB_PASSWORD)
    
    try:
        df_result, duration = analyzer.run_query_4b()
        
        if not df_result.empty:
            print("\n=== ESEMPIO RISULTATI (Primi 5) ===")
            print(df_result.head(5).to_string(index=False))
        else:
            print("\nNessun risultato.")
            print("   Verifica di aver scommentato le date giuste per il dataset caricato!")
            
    except Exception as e:
        print(f"Errore: {e}")
    finally:
        analyzer.close()