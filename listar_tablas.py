import sqlite3

def listar_tablas_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        print(f"Tablas en '{db_path}':")
        if tablas:
            for tabla in tablas:
                print(f"- {tabla[0]}")
        else:
            print("No se encontraron tablas.")
    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    listar_tablas_db('db_current_RESP.sqlite3')
