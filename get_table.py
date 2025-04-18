import sqlite3

con = sqlite3.connect('library.db')
cur = con.cursor()

print("TABLE Student:")
res = cur.execute("SELECT * FROM Student")
for i in res:
    print(i)
print("\n")

print("TABLE Admin")
res = cur.execute("SELECT  * FROM Admin")
for i in res:
    print(i)
print("\n")

print("TABLE Book:")
res = cur.execute("SELECT * FROM Book")
for i in res:
    print(i)
print("\n")

print("TABLE Record:")
res = cur.execute("SELECT * FROM Record")
for i in res:
    print(i)
print("\n")
