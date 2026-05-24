import sqlite3
import csv
from collections import defaultdict

DATABASE_PATH = 'shipment_database.db'
SHIPPING_DATA_0_PATH = 'data/shipping_data_0.csv'
SHIPPING_DATA_1_PATH = 'data/shipping_data_1.csv'
SHIPPING_DATA_2_PATH = 'data/shipping_data_2.csv'


def get_or_create_product_id(cursor, product_name):
    """
    Checks if a product exists by name. If it does, returns its ID.
    Otherwise, inserts the product and returns the new ID.
    """
    cursor.execute('SELECT id FROM product WHERE name = ?', (product_name,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        cursor.execute('INSERT INTO product (name) VALUES (?)', (product_name,))
        return cursor.lastrowid


def insert_data_from_csv_0(cursor, file_path):
    """Inserts data from shipping_data_0.csv into the product and shipment tables."""
    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip header row
        for row in reader:
            # Columns: origin_warehouse,destination_store,product,on_time,product_quantity,driver_identifier
            origin_warehouse, destination_store, product_name_from_csv, on_time_str, product_quantity_from_csv, driver_identifier = row

            product_id = get_or_create_product_id(cursor, product_name_from_csv)

            # Insert into shipment table, ignoring 'on_time' and 'driver_identifier'
            cursor.execute('''
                INSERT INTO shipment (product_id, quantity, origin, destination)
                VALUES (?, ?, ?, ?)
            ''', (product_id, int(product_quantity_from_csv), origin_warehouse, destination_store))

def insert_data_from_csv_1_and_2(cursor, file_path_1, file_path_2):
    """
    Inserts data from shipping_data_1.csv and shipping_data_2.csv into the product and shipment tables.
    shipping_data_2.csv provides origin and destination for shipment_ids found in shipping_data_1.csv.
    This function now aggregates quantities for products within the same shipment identifier.
    """
    # 1. Read shipping_data_2.csv first to get origin and destination for logical shipment_ids
    shipment_details = {}
    with open(file_path_2, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip header row
        for row in reader:
            # shipping_data_2.csv has 4 columns: shipment_identifier, origin, destination, driver_identifier
            logical_shipment_id, origin, destination, _ = row # Discard the 4th column (driver_identifier)
            shipment_details[logical_shipment_id] = {'origin': origin, 'destination': destination}

    # 2. Aggregate quantities from shipping_data_1.csv
    # Key: (logical_shipment_id, product_name), Value: total_quantity
    aggregated_products_per_shipment = defaultdict(int)
    with open(file_path_1, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip header row
        for row in reader:
            # Assuming shipping_data_1.csv has 3 columns: shipment_identifier,product,on_time
            logical_shipment_id, product_name, on_time_status = row

            # Each row represents a quantity of 1 for that product in that shipment
            aggregated_products_per_shipment[(logical_shipment_id, product_name)] += 1

    # 3. Insert aggregated data into the shipment table
    for (logical_shipment_id, product_name), total_quantity in aggregated_products_per_shipment.items():
        if logical_shipment_id in shipment_details:
            origin = shipment_details[logical_shipment_id]['origin']
            destination = shipment_details[logical_shipment_id]['destination']

            product_id = get_or_create_product_id(cursor, product_name)

            cursor.execute('''
                INSERT INTO shipment (product_id, quantity, origin, destination)
                VALUES (?, ?, ?, ?)
            ''', (product_id, total_quantity, origin, destination))
        else:
            print(f"Warning: Logical Shipment ID {logical_shipment_id} from {file_path_1} not found in {file_path_2}")

def main():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        print(f"Inserting data from {SHIPPING_DATA_0_PATH}...")
        insert_data_from_csv_0(cursor, SHIPPING_DATA_0_PATH)
        print(f"Data from {SHIPPING_DATA_0_PATH} inserted.")

        print(f"Inserting data from {SHIPPING_DATA_1_PATH} and {SHIPPING_DATA_2_PATH}...")
        insert_data_from_csv_1_and_2(cursor, SHIPPING_DATA_1_PATH, SHIPPING_DATA_2_PATH)
        print(f"Data from {SHIPPING_DATA_1_PATH} and {SHIPPING_DATA_2_PATH} inserted.")

        conn.commit()
        print("All data inserted successfully.")

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except FileNotFoundError as e:
        print(f"File not found error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()