import pandas as pd
from neo4j import GraphDatabase
import time

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678"

class Neo4jAnalyticsQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query_4a(self):
        print("   🔍 Esecuzione Query 4.a (Clienti simili su stessi terminali)...")
        print("      Attendi, questa operazione può richiedere tempo su dataset grandi...")
        start_time = time.time()
        
        # Query Cypher A
        query = """
        // 1. Trova coppie (m, n) che si sono incrociate su un terminale 't'
        MATCH (m:Customer)-[:PERFORMED]->(:Transaction)-[:OCCURRED_AT]->(t:Terminal)<-[:OCCURRED_AT]-(:Transaction)<-[:PERFORMED]-(n:Customer)
        
        // 2. Evita duplicati (m-n è uguale a n-m) e se stessi
        WHERE m.id < n.id
        
        // 3. Conta quanti terminali DISTINTI condividono
        WITH m, n, count(DISTINCT t) as shared_terminals
        
        // 4. Primo filtro: devono condividerne almeno 4
        WHERE shared_terminals >= 4
        
        // 5. Ora (e solo ora) calcoliamo il numero totale di transazioni per m e n
        MATCH (m)-[:PERFORMED]->(txM:Transaction)
        WITH m, n, shared_terminals, count(txM) as countM
        
        MATCH (n)-[:PERFORMED]->(txN:Transaction)
        WITH m, n, shared_terminals, countM, count(txN) as countN
        
        // 6. Secondo filtro: differenza transazioni <= 2
        WHERE abs(countM - countN) <= 2
        
        // 7. Risultato finale
        RETURN 
            m.id as Customer_M, 
            n.id as Customer_N, 
            shared_terminals as Shared_Terminals, 
            countM as Tx_Count_M, 
            countN as Tx_Count_N
        ORDER BY shared_terminals DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            data = [record.data() for record in result]

        elapsed = time.time() - start_time
        
        # DataFrame
        df = pd.DataFrame(data)
        
        print(f"   Query completata in {elapsed:.2f} s")
        print(f"   Trovate {len(df)} coppie di clienti.")
        return df, elapsed

if __name__ == "__main__":
    analyzer = Neo4jAnalyticsQuery(DB_URI, "neo4j", DB_PASSWORD)
    
    try:
        df_result, duration = analyzer.run_query_4a()
        
        if not df_result.empty:
            print("\n=== RISULTATI QUERY 4.a (Primi 10 risultati) ===")
            print(df_result.head(10).to_string(index=False))
        else:
            print("\nNessun cliente soddisfa i criteri (condizioni molto restrittive).")
        
    except Exception as e:
        print(f"Errore durante l'esecuzione: {e}")
    finally:
        analyzer.close()