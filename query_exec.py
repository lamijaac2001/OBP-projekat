import pyodbc
import time
import pandas as pd
import matplotlib.pyplot as plt


class QueryExecutor:
    def __init__(self, server="DESKTOP-C2MG3H7", database="StackOverflow2013"):
        # Povezivanje na SQL Server (Windows Authentication)
        self.conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'Trusted_Connection=yes;'
        )

    def run_query(self, query, runs=3):
        times = []
        cursor = self.conn.cursor()
        for i in range(runs):
            start = time.time()
            cursor.execute(query)
            try:
                cursor.fetchall()  # SELECT vraća rezultate
            except:
                pass  # INSERT/UPDATE/DELETE nemaju fetch
            end = time.time()
            times.append((end - start) * 1000)  # vrijeme u ms

        return {
            "query": query[:80] + "...",
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "avg_time_ms": sum(times) / len(times),
            "runs": runs
        }


if __name__ == "__main__":
    executor = QueryExecutor()

    #  Workload upiti (isti kao u SQL skripti)
    test_queries = [
        # 1. Top korisnici po reputaciji
        "SELECT TOP 1000 Id, DisplayName, Reputation FROM dbo.Users ORDER BY Reputation DESC;",

        # 2. Broj postova po korisniku
        """SELECT TOP 100 u.DisplayName, COUNT(p.Id) AS BrojPostova
           FROM dbo.Users u
           JOIN dbo.Posts_Test p ON u.Id = p.OwnerUserId
           GROUP BY u.DisplayName
           ORDER BY BrojPostova DESC;""",

        # 3. Broj postova po godini (Posts_Test)
        """SELECT YEAR(CreationDate) AS Godina, COUNT(*) AS BrojPostova
           FROM dbo.Posts_Test
           GROUP BY YEAR(CreationDate)
           ORDER BY Godina;""",

        # 4. Insert u Comments
        "INSERT INTO dbo.Comments (PostId, Score, Text, CreationDate, UserId) VALUES (1, 0, 'Test komentar', GETDATE(), 2);",

        # 5. Update u Posts_Test
        "UPDATE dbo.Posts_Test SET Score = Score + 1 WHERE Id < 1000;",

        # 6. Delete iz Comments
        "DELETE FROM dbo.Comments WHERE Id < 1000;",

        # 7. Broj postova po godini na particionisanoj tabeli
        """SELECT YEAR(CreationDate) AS Godina, COUNT(*) AS BrojPostova
           FROM dbo.Posts_TestPartitioned
           GROUP BY YEAR(CreationDate)
           ORDER BY Godina;"""
    ]

    results = []
    for q in test_queries:
        print(f"\n▶ Izvršavam upit:\n{q}\n")
        res = executor.run_query(q, runs=3)
        results.append(res)
        print("Rezultat:", res)

    # Spremi rezultate u CSV
    df = pd.DataFrame(results)
    df.to_csv("benchmark_results.csv", mode="a", index=False)

    #Nacrtaj graf prosječnog vremena
    plt.bar(df["query"], df["avg_time_ms"])
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.ylabel("Prosječno vrijeme (ms)")
    plt.title("Performanse SQL upita (StackOverflow Test)")
    plt.tight_layout()
    plt.show()





