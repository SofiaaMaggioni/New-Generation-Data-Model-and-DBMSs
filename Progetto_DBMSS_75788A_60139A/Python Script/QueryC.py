import pandas as pd
from neo4j import GraphDatabase
import time
import random

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678"

TARGET_CUSTOMER_ID = None

class Neo4jNetworkQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_random_customer(self):
        """Recupera un ID cliente casuale che abbia almeno una transazione."""
        print("Scelta casuale di un cliente")
        with self.driver.session() as session:
            result = session.run("""
                MATCH (c:Customer)-[:PERFORMED]->() 
                WITH c, rand() as r 
                ORDER BY r LIMIT 1 
                RETURN c.id as uid
            """)
            record = result.single()
            return record["uid"] if record else None

    def check_customer_exists(self, uid):
        """Verifica se l'ID specificato manualmente esiste davvero."""
        with self.driver.session() as session:
            result = session.run("MATCH (c:Customer {id: $uid}) RETURN c.id", uid=uid)
            return result.single() is not None

    def run_query_4c(self, target_user_id):
        print(f"   🔍 Esecuzione Query 4.c (Co-customer Network Degree 3)...")
        print(f"      Target Customer ID: {target_user_id}")
        
        start_time = time.time()
        
        # Query Cypher per CN_3(u)
        # Livello 1: u1 -> t1 -> u2 (condividono t1)
        # Livello 2: u2 -> t2 -> u3 (condividono t2)
        query = """
        MATCH (u1:Customer {id: $uid})
        
        // Passaggio 1: Trova u2 (Clienti che hanno condiviso un terminale con u1)
        MATCH (u1)-[:PERFORMED]->(:Transaction)-[:OCCURRED_AT]->(t1:Terminal)<-[:OCCURRED_AT]-(:Transaction)<-[:PERFORMED]-(u2:Customer)
        WHERE u2 <> u1
        
        // Passaggio 2: Trova u3 (Clienti che hanno condiviso un terminale con u2)
        MATCH (u2)-[:PERFORMED]->(:Transaction)-[:OCCURRED_AT]->(t2:Terminal)<-[:OCCURRED_AT]-(:Transaction)<-[:PERFORMED]-(u3:Customer)
        WHERE u3 <> u1 AND u3 <> u2
        
        // Output: Contiamo quanti utenti unici ci sono nel livello 3
        RETURN 
            count(DISTINCT u3) as network_size,
            collect(DISTINCT u3.id)[0..10] as sample_members
        """
        
        record = None
        try:
            with self.driver.session() as session:
                result = session.run(query, uid=target_user_id)
                record = result.single()
        except Exception as e:
            print(f"Errore durante l'esecuzione della query: {e}")
            # If there is an out-of-memory error
            if "MemoryPoolOutOfMemoryError" in str(e):
                print("MEMORIA ESAURITA! Il network è troppo grande per la RAM attuale.")

        # --- STOP TIMER ---
        elapsed = time.time() - start_time
        print(f"   ⏱️  Tempo Query: {elapsed:.2f} s") 
        
        if record:
            size = record["network_size"]
            sample = record["sample_members"]
            print(f"      Dimensione Network CN_3: {size} utenti")
            print(f"      Esempio membri (primi 10): {sample}")
            return elapsed
        else:
            print("Nessun risultato trovato (Record vuoto o query fallita).")
            return elapsed

if __name__ == "__main__":
    analyzer = Neo4jNetworkQuery(DB_URI, "neo4j", DB_PASSWORD)
    
    try:
        final_id = None
        
        if TARGET_CUSTOMER_ID is not None:
            if analyzer.check_customer_exists(TARGET_CUSTOMER_ID):
                final_id = TARGET_CUSTOMER_ID
            else:
                print(f"Errore: Il cliente {TARGET_CUSTOMER_ID} non esiste nel DB!")
        else:
            # Altrimenti random
            final_id = analyzer.get_random_customer()
        
        if final_id is not None:
            duration = analyzer.run_query_4c(final_id)
            print("\n" + "="*40)
            print(f" RISULTATO FINALE TEMPO: {duration:.2f} secondi")
            print("="*40)
        else:
            print("Errore: Nessun cliente valido trovato.")
            
    except Exception as e:
        print(f"Errore generico: {e}")
    finally:
        analyzer.close()