import pandas as pd
from neo4j import GraphDatabase
import time

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678"

# --- OPZIONE 1: DATASET SMALL (97 Days) ---
#START_PREV = "2025-01-01"
#END_PREV   = "2025-03-31"
#START_CURR = "2025-04-01"
#END_CURR   = "2025-04-10"

# --- OPZIONE 2: DATASET MEDIUM (187 Days) e LARGE (367 Days) ---
START_PREV = "2025-01-01"
END_PREV   = "2025-03-31"
START_CURR = "2025-04-01"
END_CURR   = "2025-06-30"


class Neo4jAnalyticsQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query_4e_custom(self):
        print("Esecuzione Query 4.e")
        print(f"      Baseline (Prev): {START_PREV} -> {END_PREV}")
        print(f"      Analisi  (Curr): {START_CURR} -> {END_CURR}")
        
        start_time = time.time()
        
        # 1. Trova le transazioni del periodo PREV e calcola la mediana per terminale.
        # 2. Trova le transazioni del periodo CURR.
        # 3. Confronta (Current Amount > 1.3 * Prev Median).
        # 4. Raggruppa per Giorno della Settimana.

        query = """
        // --- PARTE 1: Calcolo Mediana Storica (Periodo PREV) ---
        MATCH (t:Terminal)<-[:OCCURRED_AT]-(tx_prev:Transaction)
        WHERE date(datetime(replace(tx_prev.date, ' ', 'T'))) >= date($start_prev) 
          AND date(datetime(replace(tx_prev.date, ' ', 'T'))) <= date($end_prev)
        
        WITH t, percentileCont(tx_prev.amount, 0.5) as median_prev
        
        // --- PARTE 2: Analisi Transazioni Correnti (Periodo CURR) ---
        MATCH (t)<-[:OCCURRED_AT]-(tx_curr:Transaction)
        WHERE date(datetime(replace(tx_curr.date, ' ', 'T'))) >= date($start_curr) 
          AND date(datetime(replace(tx_curr.date, ' ', 'T'))) <= date($end_curr)
          
        // Estrazione Giorno della Settimana (1=Lun, 7=Dom)
        WITH t, median_prev, tx_curr, 
             datetime(replace(tx_curr.date, ' ', 'T')).dayOfWeek as day_number
        
        // --- PARTE 3: Applicazione Logica Outlier (3.b) ---
        // Outlier se l'importo corrente supera del 30% la mediana storica del terminale
        WITH day_number, tx_curr, 
             (tx_curr.amount > (1.3 * median_prev)) AS is_outlier

        // --- PARTE 4: Aggregazione ---
        RETURN 
            day_number,
            count(tx_curr) AS total_transactions,
            sum(CASE WHEN is_outlier THEN 1 ELSE 0 END) AS outlier_count
        ORDER BY day_number
        """
        
        parameters = {
            "start_prev": START_PREV, "end_prev": END_PREV,
            "start_curr": START_CURR, "end_curr": END_CURR
        }
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                data = [record.data() for record in result]
                
            elapsed = time.time() - start_time
            
            # --- Creation Pandas DataFrame ---
            df = pd.DataFrame(data)
            
            if not df.empty:
                # Calcolo %
                df['proportion_outliers (%)'] = (df['outlier_count'] / df['total_transactions']) * 100
                df['proportion_outliers (%)'] = df['proportion_outliers (%)'].round(2)
                
                # Mapping days's name
                days_map = {
                    1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 
                    5: 'Friday', 6: 'Saturday', 7: 'Sunday'
                }
                df['day_name'] = df['day_number'].map(days_map)
                
                # Reordering columns
                df = df[['day_number', 'day_name', 'total_transactions', 'outlier_count', 'proportion_outliers (%)']]
                
                print(f"Query completata in {elapsed:.2f} s")
                return df, elapsed
            else:
                print("Nessun dato trovato nel periodo selezionato.")
                return pd.DataFrame(), elapsed

        except Exception as e:
            print(f"Errore esecuzione query: {e}")
            return pd.DataFrame(), 0

if __name__ == "__main__":
    analyzer = Neo4jAnalyticsQuery(DB_URI, "neo4j", DB_PASSWORD)
    
    try:
        df_result, duration = analyzer.run_query_4e_custom()
        
        if not df_result.empty:
            print("\n=== RISULTATI QUERY 4.e (Summary Table) ===")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(df_result.to_string(index=False))
            
            print("\n" + "="*40)
            print(f" TEMPO TOTALE: {duration:.4f} s")
            print("="*40)
            
            
    except KeyboardInterrupt:
        print("\nInterrotto manualmente.")
    finally:
        analyzer.close()