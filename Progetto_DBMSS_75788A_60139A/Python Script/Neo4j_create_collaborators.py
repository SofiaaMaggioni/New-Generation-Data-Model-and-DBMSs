from neo4j import GraphDatabase
import time

# ================= CONFIGURATION =================
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678"  

class Neo4jCollaboratorLinker:
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

    def step_1_calculate_avg_satisfaction(self):
        print("Fase 1: Calcolo media soddisfazione")
        start_time = time.time()
        
        query = """
        MATCH (c:Customer)-[:PERFORMED]->(tx:Transaction)
        WHERE tx.satisfaction IS NOT NULL
        WITH c, avg(tx.satisfaction) as calculated_avg
        SET c.avg_satisfaction = calculated_avg
        RETURN count(c) as processed_customers
        """
        
        with self.driver.session() as session:
            session.run(query)
            
        return time.time() - start_time

    def get_all_terminal_ids(self):
        """Scarica tutti gli ID dei terminali per gestirli in Python (evita loop infiniti)"""
        with self.driver.session() as session:
            result = session.run("MATCH (t:Terminal) RETURN t.id as tid")
            return [record["tid"] for record in result]

    def step_2_create_relationships_safe(self, batch_size=1000):
        print("Fase 2: Creazione relazioni")
        start_time = time.time()
        
        # 1. Recuperiamo tutti gli ID dei terminali per evitare loop infiniti
        terminal_ids = self.get_all_terminal_ids()
        total_terminals = len(terminal_ids)
        print(f"      -> Trovati {total_terminals} terminali da analizzare.")

        # Query ottimizzata e senza warning deprecati
        query = """
        UNWIND $batch_ids AS tid
        MATCH (t:Terminal {id: tid})
        
        // Trova clienti che hanno usato QUESTO terminale almeno 5 volte
        MATCH (c:Customer)-[:PERFORMED]->(tx:Transaction)-[:OCCURRED_AT]->(t)
        WITH t, c, count(tx) as tx_count
        WHERE tx_count >= 5
        
        // Raggruppa i clienti per quel terminale
        WITH t, collect({cust: c, sat: c.avg_satisfaction}) as frequent_users
        WHERE size(frequent_users) > 1
        
        // Confronta ogni cliente con tutti gli altri
        UNWIND frequent_users as u1
        UNWIND frequent_users as u2
        
        // Filtra duplicati e condizione soddisfazione
        // NOTA: Usiamo elementId() invece di id() per evitare i warning
        WITH u1, u2
        WHERE elementId(u1.cust) < elementId(u2.cust)
        AND abs(u1.sat - u2.sat) <= 0.5
        
        // Assegnazione variabili semplici per il MERGE
        WITH u1.cust AS c1, u2.cust AS c2
        
        MERGE (c1)-[r:FREQUENT_COLLABORATOR]->(c2)
        RETURN count(r) as created_rels
        """
        
        total_rels = 0
        
        # 2. we process in batches to avoid long transactions
        with self.driver.session() as session:
            for i in range(0, total_terminals, batch_size):
                # take a piece of the list (es. da 0 a 1000)
                batch_ids = terminal_ids[i : i + batch_size]
                
                result = session.run(query, batch_ids=batch_ids)
                record = result.single()
                
                if record:
                    total_rels += record["created_rels"]

        
        elapsed = time.time() - start_time
        print(f"\n      -> Relazioni create: {total_rels}")
        return elapsed

if __name__ == "__main__":
    linker = Neo4jCollaboratorLinker(DB_URI, "neo4j", DB_PASSWORD)
    
    try:
        t1 = linker.step_1_calculate_avg_satisfaction()
        t2 = linker.step_2_create_relationships_safe()
        
        print("\n" + "="*40)
        print(f" TEMPO TOTALE: {t1 + t2:.2f} s")
        print("="*40)
        
    except KeyboardInterrupt:
        print("\n Interrotto dall'utente.")
    finally:
        linker.close()