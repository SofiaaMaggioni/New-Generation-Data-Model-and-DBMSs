from neo4j import GraphDatabase
import time

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678"

class Neo4jUpdater:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print(f"Connesso a Neo4j su {uri}")
        except Exception as e:
            print(f"Errore connessione: {e}")
            exit(1)

    def close(self):
        self.driver.close()

    def update_transactions(self, batch_size=10000):
        """
        Aggiorna le transazioni aggiungendo:
        a. payment_method (random)
        b. promo (boolean random)
        c. satisfaction (1-5 random)
        
        Usa i batch per evitare di saturare la memoria RAM.
        """
        print("Inizio aggiornamento transazioni (Arricchimento dati)")
        
        # This query finds transactions that do NOT yet have the 'payment_method',the 'promo' property and 'satisfaction' property.
        query = """
        MATCH (t:Transaction)
        WHERE t.payment_method IS NULL
        WITH t LIMIT $batch_size
        
        // Generazione casuale dei dati
        SET t.payment_method = CASE toInteger(rand() * 3)
            WHEN 0 THEN 'Credit Card'
            WHEN 1 THEN 'Mobile Payment'
            ELSE 'PayPal' END,
            
            // 15% Di probabilità che sia una promo (puoi cambiare 0.15 a piacere)
            t.promo = CASE WHEN rand() < 0.15 THEN true ELSE false END, 
            
            // Rating da 1 a 5
            t.satisfaction = toInteger(rand() * 5) + 1
            
        RETURN count(t) as updated_count
        """
        
        total_updated = 0
        start_time = time.time()
        
        with self.driver.session() as session:
            while True:
                result = session.run(query, batch_size=batch_size)
                count = result.single()["updated_count"]
                
                total_updated += count
                print(f"      -> Aggiornate {count} transazioni (Totale parziale: {total_updated})")
                
                # If the count is 0, it means there are no more transactions to update
                if count == 0:
                    break
        
        elapsed = time.time() - start_time
        return total_updated, elapsed

if __name__ == "__main__":
    updater = Neo4jUpdater(DB_URI, "neo4j", DB_PASSWORD)
    
    try:
        total, duration = updater.update_transactions()
        
        print("\nAGGIORNAMENTO COMPLETATO!")
        print(f"   Transazioni modificate: {total}")
        print(f"   Tempo impiegato: {duration:.2f} secondi")
        
    finally:
        updater.close()