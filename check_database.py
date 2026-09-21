import sqlite3

db = r"D:\NEW PROJECT IMRAN\file_database.db"

con = sqlite3.connect(db)
cur = con.cursor()

print("\nCOLUMNS:")
columns = cur.execute("PRAGMA table_info(datasets)").fetchall()

for col in columns:
    print(col)

print("\nOLD DATA:")
rows = cur.execute("SELECT * FROM datasets").fetchall()

for row in rows:
    print(row)

con.close()
