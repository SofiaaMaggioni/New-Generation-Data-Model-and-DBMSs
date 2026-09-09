import numpy as np
import pandas as pd
import time
import random
import os

# ==========================================
# 1. FUNZIONI DEL SIMULATORE
# ==========================================

def generate_customer_profiles_table(n_customers, random_state=0):
    np.random.seed(random_state)
    customer_id_properties = []
    
    # Generate customer properties from random distributions
    for customer_id in range(n_customers):
        x_customer_id = np.random.uniform(0, 100)
        y_customer_id = np.random.uniform(0, 100)
        
        mean_amount = np.random.uniform(5, 100) # Arbitrary (but sensible) value
        std_amount = mean_amount / 2 # Arbitrary (but sensible) value
        
        mean_nb_tx_per_day = np.random.uniform(0, 4) # Arbitrary (but sensible) value
        
        customer_id_properties.append([customer_id,
                                      x_customer_id, y_customer_id,
                                      mean_amount, std_amount,
                                      mean_nb_tx_per_day])
        
    customer_profiles_table = pd.DataFrame(customer_id_properties,
                                           columns=['CUSTOMER_ID',
                                                    'x_customer_id', 'y_customer_id',
                                                    'mean_amount', 'std_amount',
                                                    'mean_nb_tx_per_day'])
    return customer_profiles_table

def generate_terminal_profiles_table(n_terminals, random_state=0):
    np.random.seed(random_state)
    terminal_id_properties = []
    
    # Generate terminal properties from random distributions
    for terminal_id in range(n_terminals):
        x_terminal_id = np.random.uniform(0, 100)
        y_terminal_id = np.random.uniform(0, 100)
        
        terminal_id_properties.append([terminal_id,
                                       x_terminal_id, y_terminal_id])
                                       
    terminal_profiles_table = pd.DataFrame(terminal_id_properties,
                                           columns=['TERMINAL_ID',
                                                    'x_terminal_id', 'y_terminal_id'])
    return terminal_profiles_table

def get_list_terminals_within_radius(customer_profile, x_y_terminals, r):
       
    # Location (x,y) of customer as numpy array
    x_y_customer = customer_profile[['x_customer_id','y_customer_id']].values.astype(float)
    
    # Squared difference in coordinates between customer and terminal locations
    squared_diff_x_y = np.square(x_y_customer - x_y_terminals)
    
    # Sum along rows and compute squared root to get distance
    dist_x_y = np.sqrt(np.sum(squared_diff_x_y, axis=1))
    
    # Get the indices of terminals which are at a distance less than r
    available_terminals = list(np.where(dist_x_y < r)[0])
    
    return available_terminals

def generate_transactions_table(customer_profile, start_date="2018-04-01", nb_days=10):
    customer_transactions = []
    
    random.seed(int(customer_profile.CUSTOMER_ID))
    np.random.seed(int(customer_profile.CUSTOMER_ID))
    
    for day in range(nb_days):
        # Random number of transactions for that day
        nb_tx = np.random.poisson(customer_profile.mean_nb_tx_per_day)
        
        # If nb_tx positive, let us generate transactions
        if nb_tx > 0:
            for tx in range(nb_tx):
                # Time of transaction: std 20000 seconds.
                # This choice aims at simulating the fact that most transactions occur during the day.
                time_tx = int(np.random.normal(86400/2, 20000))
                
                # If transaction time between 0 and 86400, we keep it, otherwise, we discard it
                if (time_tx > 0) and (time_tx < 86400):
                    
                    # Amount is drawn from a normal distribution
                    amount = np.random.normal(customer_profile.mean_amount, 
                                              customer_profile.std_amount)
                    
                    # If amount negative, draw from a uniform distribution
                    if amount < 0:
                        amount = np.random.uniform(0, customer_profile.mean_amount * 2)
                    
                    amount = np.round(amount, decimals=2)
                    
                    if len(customer_profile.available_terminals) > 0:
                        terminal_id = random.choice(customer_profile.available_terminals)
                        
                        customer_transactions.append([time_tx + day * 86400,
                                                      day,
                                                      customer_profile.CUSTOMER_ID,
                                                      terminal_id,
                                                      amount])
                                                      
    customer_transactions = pd.DataFrame(customer_transactions, 
                                         columns=['TX_TIME_SECONDS', 'TX_TIME_DAYS', 
                                                  'CUSTOMER_ID', 'TERMINAL_ID', 
                                                  'TX_AMOUNT'])
    
    if len(customer_transactions) > 0:
        customer_transactions['TX_DATETIME'] = pd.to_datetime(customer_transactions['TX_TIME_SECONDS'], 
                                                              unit='s', origin=start_date)
        
        customer_transactions = customer_transactions[['TX_DATETIME', 'CUSTOMER_ID',
                                                       'TERMINAL_ID', 'TX_AMOUNT', 
                                                       'TX_TIME_SECONDS', 'TX_TIME_DAYS']]
                                                       
    return customer_transactions

def add_frauds(customer_profiles_table, terminal_profiles_table, transactions_df):
    
    # By default, all transactions are genuine
    transactions_df['TX_FRAUD'] = 0
    transactions_df['TX_FRAUD_SCENARIO'] = 0
    
    # Scenario 1
    transactions_df.loc[transactions_df.TX_AMOUNT > 220, 'TX_FRAUD'] = 1
    transactions_df.loc[transactions_df.TX_AMOUNT > 220, 'TX_FRAUD_SCENARIO'] = 1
    
    nb_frauds_scenario_1 = transactions_df.TX_FRAUD.sum()
    print("Number of frauds from scenario 1: " + str(nb_frauds_scenario_1))
    
    # Scenario 2 two terminals are compromised for 28 days, and all transactions occurring on these terminals during this period are fraudulent
    for day in range(transactions_df.TX_TIME_DAYS.max()):
        compromised_terminals = terminal_profiles_table.TERMINAL_ID.sample(n=2, random_state=day)
        
        compromised_transactions = transactions_df[(transactions_df.TX_TIME_DAYS >= day) & 
                                                   (transactions_df.TX_TIME_DAYS < day + 28) & 
                                                   (transactions_df.TERMINAL_ID.isin(compromised_terminals))]
        
        transactions_df.loc[compromised_transactions.index, 'TX_FRAUD'] = 1
        transactions_df.loc[compromised_transactions.index, 'TX_FRAUD_SCENARIO'] = 2
        
    nb_frauds_scenario_2 = transactions_df.TX_FRAUD.sum() - nb_frauds_scenario_1
    print("Number of frauds from scenario 2: " + str(nb_frauds_scenario_2))
    
    # Scenario 3
    for day in range(transactions_df.TX_TIME_DAYS.max()):
        compromised_customers = customer_profiles_table.CUSTOMER_ID.sample(n=3, random_state=day).values
        
        compromised_transactions = transactions_df[(transactions_df.TX_TIME_DAYS >= day) & 
                                                   (transactions_df.TX_TIME_DAYS < day + 14) & 
                                                   (transactions_df.CUSTOMER_ID.isin(compromised_customers))]
        
        nb_compromised_transactions = len(compromised_transactions)
        
        random.seed(day)
        if nb_compromised_transactions > 0:
            index_frauds = random.sample(list(compromised_transactions.index.values), 
                                         k=int(nb_compromised_transactions / 3))
            
            transactions_df.loc[index_frauds, 'TX_AMOUNT'] = transactions_df.loc[index_frauds, 'TX_AMOUNT'] * 5
            transactions_df.loc[index_frauds, 'TX_FRAUD'] = 1
            transactions_df.loc[index_frauds, 'TX_FRAUD_SCENARIO'] = 3
            
    nb_frauds_scenario_3 = transactions_df.TX_FRAUD.sum() - nb_frauds_scenario_2 - nb_frauds_scenario_1
    print("Number of frauds from scenario 3: " + str(nb_frauds_scenario_3))
    
    return transactions_df

# ==========================================
# 2. IMPLEMENTATION (Punto 1)
# ==========================================

def generate_project_datasets():
    print("=== Inizio Generazione Profili (Fixed per tutti i dataset) ===")
    
    # We use 5000 clients e 10000 terminals
    n_customers = 5000
    n_terminals = 10000
    radius = 5
    start_date = "2025-01-01"

    # 1. Generation of base tables (Clients e Terminals) - made only one time
    start_time = time.time()
    customer_profiles_table = generate_customer_profiles_table(n_customers, random_state=0)
    print(f"Customer profiles generated: {len(customer_profiles_table)} rows.")
    
    terminal_profiles_table = generate_terminal_profiles_table(n_terminals, random_state=1)
    print(f"Terminal profiles generated: {len(terminal_profiles_table)} rows.")

    # 2. Associations of Terminals to Customers
    print("Associating terminals to customers (this may take a moment)...")
    x_y_terminals = terminal_profiles_table[['x_terminal_id', 'y_terminal_id']].values.astype(float)
    customer_profiles_table['available_terminals'] = customer_profiles_table.apply(
        lambda x: get_list_terminals_within_radius(x, x_y_terminals=x_y_terminals, r=radius), axis=1
    )
    customer_profiles_table['nb_terminals'] = customer_profiles_table.available_terminals.apply(len)
    print(f"Association done. Time elapsed: {time.time()-start_time:.2f}s")

    # Save the profiles (equal for all datasets)
    if not os.path.exists('output_datasets'):
        os.makedirs('output_datasets')
    
    customer_profiles_table.to_csv('output_datasets/customer_profiles.csv', index=False)
    terminal_profiles_table.to_csv('output_datasets/terminal_profiles.csv', index=False)
    print("Profili salvati in 'output_datasets/'.")

    # Save and check size CUSTOMER
    cust_filename = 'output_datasets/customer_profiles.csv'
    customer_profiles_table.to_csv(cust_filename, index=False)
    cust_size_mb = os.path.getsize(cust_filename) / (1024 * 1024)
    print(f"-> File salvato: {cust_filename} | Dimensione: {cust_size_mb:.2f} MB")

    # Save and check size TERMINAL
    term_filename = 'output_datasets/terminal_profiles.csv'
    terminal_profiles_table.to_csv(term_filename, index=False)
    term_size_mb = os.path.getsize(term_filename) / (1024 * 1024)
    print(f"-> File salvato: {term_filename} | Dimensione: {term_size_mb:.2f} MB")

    # Generation of the 3 transaction datasets (increasing sizes)
    # Estimation: 5000 customers generate about 1.7M transactions in 180 days (~100MB)
    # Target: 50MB, 100MB, 200MB
    # Estimated days: 45 days (~50MB), 90 days (~100MB), 180 days (~200MB)

    dataset_configs = [
        ("dataset_small_50MB", 97),
        ("dataset_medium_100MB", 187),
        ("dataset_large_200MB", 367)
    ]

    for name, nb_days in dataset_configs:
        print(f"\n--- Generazione {name} ({nb_days} giorni) ---")
        gen_start = time.time()
        
        # Generation of Transactions
        transactions_df = customer_profiles_table.groupby('CUSTOMER_ID').apply(
            lambda x: generate_transactions_table(x.iloc[0], start_date=start_date, nb_days=nb_days)
        ).reset_index(drop=True)
        
        # Order chronologically and reset index (Transaction ID)
        transactions_df = transactions_df.sort_values('TX_DATETIME')
        transactions_df.reset_index(inplace=True, drop=True)
        transactions_df.reset_index(inplace=True)
        transactions_df.rename(columns={'index': 'TRANSACTION_ID'}, inplace=True)
        
        print(f"Transazioni base generate: {len(transactions_df)}")
        
        # Add Frauds (Scenario 1, 2, 3)
        print("Aggiunta scenari di frode...")
        transactions_df = add_frauds(customer_profiles_table, terminal_profiles_table, transactions_df)
        
        # Save to CSV
        filename = f"output_datasets/{name}.csv"
        transactions_df.to_csv(filename, index=False)
        
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        print(f"Completato: {filename}")
        print(f"Dimensione file: {file_size_mb:.2f} MB")
        print(f"Tempo impiegato: {time.time() - gen_start:.2f}s")

# ==========================================
# EXECUTION
# ==========================================

if __name__ == "__main__":
    generate_project_datasets()