import pandas as pd
from neo4j import GraphDatabase
import time
import random

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678" 

class Neo4jNetworkQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_random_customer(self):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Customer)-[:PERFORMED]->() 
                WITH c, rand() as r 
                ORDER BY r LIMIT 1 
                RETURN c.id as uid
            """)
            record = result.single()
            return record["uid"] if record else None

    def run_query_4c_lite(self, target_user_id):
        print(f"   🔍 Esecuzione Query 4.c LITE (Con Limit)...")
        print(f"      Target Customer ID: {target_user_id}")
        
        start_time = time.time()
        
        # Query OTTIMIZZATA con LIMIT
        # Limitiamo il numero di 'u2' (intermediari) a 100 per evitare l'esplosione
        query = """
        MATCH (u1:Customer {id: $uid})
        
        // Step 1: Trova u2 (livello 2)
        MATCH (u1)-[:PERFORMED]->(:Transaction)-[:OCCURRED_AT]->(t1:Terminal)<-[:OCCURRED_AT]-(:Transaction)<-[:PERFORMED]-(u2:Customer)
        WHERE u2 <> u1
        
        // --- LIMITATORE ---
        // Prendiamo solo i primi 100 'amici' intermediari per non bloccare il PC
        WITH u1, u2 LIMIT 100
        
        // Step 2: Trova u3 (livello 3) partendo solo da quei 100
        MATCH (u2)-[:PERFORMED]->(:Transaction)-[:OCCURRED_AT]->(t2:Terminal)<-[:OCCURRED_AT]-(:Transaction)<-[:PERFORMED]-(u3:Customer)
        WHERE u3 <> u1 AND u3 <> u2
        
        RETURN 
            count(DISTINCT u3) as network_size,
            collect(DISTINCT u3.id)[0..10] as sample_members
        """
        
        with self.driver.session() as session:
            result = session.run(query, uid=target_user_id)
            record = result.single()

        elapsed = time.time() - start_time
        print(f"Tempo Query (LITE): {elapsed:.2f} s")
        
        if record:
            print(f"  Dimensione Network (Approssimata): {record['network_size']}")
            print(f"  Esempio membri: {record['sample_members']}")
        return elapsed

if __name__ == "__main__":
    analyzer = Neo4jNetworkQuery(DB_URI, "neo4j", DB_PASSWORD)
    try:
        target_id = analyzer.get_random_customer()
        if target_id:
            analyzer.run_query_4c_lite(target_id)
    except KeyboardInterrupt:
        print("\nInterrotto manualmente.")
    finally:
        analyzer.close()