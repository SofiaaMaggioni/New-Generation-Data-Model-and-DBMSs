import pandas as pd
from neo4j import GraphDatabase
import time
import os
import ast

# ================= USER CONFIGURATION =================

# 1. choosing a dataset size
SCENARIO_TARGET = "SMALL"
#SCENARIO_TARGET = "MEDIUM"
#SCENARIO_TARGET = "LARGE"

# 2. Neo4j Connection
DB_URI = "neo4j://localhost:7687"
DB_PASSWORD = "12345678"

# 3. Data Folder
DATA_FOLDER = "output_datasets"

# ================= FILE MAP =================
FILES_MAP = {
    "SMALL": "dataset_small_50MB.csv",
    "MEDIUM": "dataset_medium_100MB.csv",
    "LARGE": "dataset_large_200MB.csv"
}

# ================= CLASS LOADER =================
class Neo4jSingleLoader:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print(f"Connesso al Database attivo su {uri}")
        except Exception as e:
            print(f"Errore connessione: {e}")
            exit(1)

    def close(self):
        self.driver.close()

    def clear_database(self):
        print("Pulizia TOTALE del database corrente...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            # remove old constraints
            try:
                session.run("DROP CONSTRAINT customer_id IF EXISTS")
                session.run("DROP CONSTRAINT terminal_id IF EXISTS")
                session.run("DROP CONSTRAINT transaction_id IF EXISTS")
            except:
                pass

    def create_constraints(self):
        print("Creazione Constraints (Indici)...")
        queries = [
            "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT terminal_id IF NOT EXISTS FOR (t:Terminal) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (tx:Transaction) REQUIRE tx.id IS UNIQUE"
        ]
        with self.driver.session() as session:
            for q in queries:
                session.run(q)

    def load_batch(self, query, df, batch_size=5000):
        total = len(df)
        with self.driver.session() as session:
            for i in range(0, total, batch_size):
                batch = df.iloc[i:i+batch_size].to_dict('records')
                session.run(query, batch=batch)

    # --- Load functions ---
    def load_customers(self, filepath):
        print(f"Caricamento CUSTOMERS da {filepath}")
        start = time.time()
        df = pd.read_csv(filepath)

        # --- CORREZIONE EVENTUALI ERRORI ---
        # Questa funzione prova a convertire la stringa in lista.
        # Se fallisce (perché i dati sono sporchi), restituisce una lista vuota [] invece di crashare.
        def safe_parse_list(x):
            if not isinstance(x, str):
                return []
            try:
                val = ast.literal_eval(x)
                if isinstance(val, list):
                    return val
                return []
            except (ValueError, SyntaxError):
                return []

        if 'available_terminals' in df.columns:
            df['available_terminals'] = df['available_terminals'].apply(safe_parse_list)

        query = """
        UNWIND $batch AS row
        MERGE (c:Customer {id: toInteger(row.CUSTOMER_ID)})
        SET c.x_coord = toFloat(row.x_customer_id),
            c.y_coord = toFloat(row.y_customer_id),
            c.mean_amount = toFloat(row.mean_amount),
            c.std_amount = toFloat(row.std_amount),
            c.mean_nb_tx_pDay = toFloat(row.mean_nb_tx_per_day)
        """
        self.load_batch(query, df)
        return time.time() - start

    def load_terminals(self, filepath):
        print("Caricamento TERMINALS")
        df = pd.read_csv(filepath)
        query = """
        UNWIND $batch AS row
        MERGE (t:Terminal {id: toInteger(row.TERMINAL_ID)})
        SET t.x_coord = toFloat(row.x_terminal_id),
            t.y_coord = toFloat(row.y_terminal_id)
        """
        start = time.time()
        self.load_batch(query, df)
        return time.time() - start

    def load_transactions(self, filepath):
        print(f"Caricamento TRANSACTIONS ({SCENARIO_TARGET})")
        df = pd.read_csv(filepath)
        query = """
        UNWIND $batch AS row
        CREATE (tx:Transaction {id: toInteger(row.TRANSACTION_ID)})
        SET tx.date = row.TX_DATETIME,
            tx.amount = toFloat(row.TX_AMOUNT),
            tx.fraud = toInteger(row.TX_FRAUD)
        
        WITH tx, row
        MATCH (c:Customer {id: toInteger(row.CUSTOMER_ID)})
        MATCH (t:Terminal {id: toInteger(row.TERMINAL_ID)})
        
        CREATE (c)-[:PERFORMED]->(tx)
        CREATE (tx)-[:OCCURRED_AT]->(t)
        """
        start = time.time()
        self.load_batch(query, df)
        return time.time() - start

def run_single_load():
    print(f"\n{'='*30}")
    print(f" AVVIO CARICAMENTO DATASET: {SCENARIO_TARGET}")
    print(f"{'='*30}")

    # File paths
    file_cust = os.path.join(DATA_FOLDER, "customer_profiles.csv")
    file_term = os.path.join(DATA_FOLDER, "terminal_profiles.csv")
    file_tx = os.path.join(DATA_FOLDER, FILES_MAP[SCENARIO_TARGET])

    # Check files exist
    if not os.path.exists(file_tx):
        print(f"ERRORE: Il file {file_tx} non esiste nella cartella {DATA_FOLDER}")
        return

    loader = Neo4jSingleLoader(DB_URI, "neo4j", DB_PASSWORD)

    try:
        # 1. Clean the current DB
        loader.clear_database()
        loader.create_constraints()

        # 2. Start Total Timer
        total_start = time.time()

        # 3. Load Data
        t_cust = loader.load_customers(file_cust)
        t_term = loader.load_terminals(file_term)
        t_tx = loader.load_transactions(file_tx)

        total_end = time.time() - total_start

        # 4. Risult Summary
        print("\n CARICAMENTO COMPLETATO CON SUCCESSO!")
        print(f"--- Tempi per Dataset {SCENARIO_TARGET} ---")
        print(f"Customer Load:    {t_cust:.2f} s")
        print(f"Terminal Load:    {t_term:.2f} s")
        print(f"Transaction Load: {t_tx:.2f} s")
        print(f"--------------------------------")
        print(f"TEMPO TOTALE:     {total_end:.2f} s")
        print("Salvati questi tempi per il report finale!")

    finally:
        loader.close()

if __name__ == "__main__":
    run_single_load()