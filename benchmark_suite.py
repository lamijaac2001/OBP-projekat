# Workload po fazama (svi upiti koriste dbo. prefiks)
WORKLOAD = {
    "baseline": [
        # 1) Top 50 korisnika po score-u odgovora
        """
        SELECT TOP (50) 
            u.Id, 
            u.DisplayName, 
            SUM(p.Score) AS TotalAnswerScore,
            COUNT(p.Id) AS NumAnswers,
            MIN(p.CreationDate) AS FirstAnswerDate,
            MAX(p.CreationDate) AS LastAnswerDate
        FROM dbo.Posts_Test p
        JOIN dbo.Users u ON u.Id = p.OwnerUserId
        WHERE p.PostTypeId = 2
        GROUP BY u.Id, u.DisplayName
        ORDER BY TotalAnswerScore DESC;
        """,

        # 2) Trend broja pitanja po mjesecu i tagu (XML parsing)
        """
        ;WITH SplitTags AS (
            SELECT
                DATEFROMPARTS(YEAR(CreationDate), MONTH(CreationDate), 1) AS MonthStart,
                LTRIM(RTRIM(m.n.value('.', 'VARCHAR(100)'))) AS TagName
            FROM dbo.Posts_Test
            CROSS APPLY (SELECT CAST('<x>' + REPLACE(REPLACE(Tags,'<',''),'>','</x><x>') + '</x>' AS XML) AS xmlTags) AS t
            CROSS APPLY xmlTags.nodes('/x') AS m(n)
            WHERE PostTypeId = 1
        ),
        TagCounts AS (
            SELECT
                TagName,
                MonthStart,
                COUNT(*) AS NumQuestions
            FROM SplitTags
            GROUP BY TagName, MonthStart
        )
        SELECT *
        FROM TagCounts
        ORDER BY MonthStart, NumQuestions DESC;
        """,

        # 3) Ko-pojavljivanje tagova (top 100 parova)
        """
        ;WITH PostTagList AS (
            SELECT
                p.Id AS PostId,
                LTRIM(RTRIM(x.n.value('.', 'VARCHAR(100)'))) AS TagName
            FROM dbo.Posts_Test p
            CROSS APPLY (
                SELECT CAST('<x>' + REPLACE(REPLACE(p.Tags,'<',''),'>','</x><x>') + '</x>' AS XML) AS xmlTags
            ) AS t
            CROSS APPLY xmlTags.nodes('/x') AS x(n)
            WHERE p.PostTypeId = 1
        ),
        TagPairs AS (
            SELECT
                pt1.TagName AS TagA,
                pt2.TagName AS TagB
            FROM PostTagList pt1
            JOIN PostTagList pt2 
              ON pt1.PostId = pt2.PostId 
             AND pt1.TagName < pt2.TagName
        )
        SELECT TOP (100)
            TagA, TagB, COUNT(*) AS PairCount
        FROM TagPairs
        GROUP BY TagA, TagB
        ORDER BY PairCount DESC;
        """,

        # 4) Lookup svih pitanja sa prihvaćenim odgovorom
        """
        SELECT 
            q.Id AS QuestionId,
            q.Title AS QuestionTitle,
            q.Score AS QuestionScore,
            q.CreationDate AS QuestionDate,
            a.Id AS AcceptedAnswerId,
            a.Score AS AnswerScore,
            a.OwnerUserId AS AnswerOwner,
            a.CreationDate AS AnswerDate
        FROM dbo.Posts_Test q
        LEFT JOIN dbo.Posts_Test a
            ON a.Id = q.AcceptedAnswerId
        WHERE q.PostTypeId = 1
        ORDER BY q.CreationDate DESC;
        """,

        # 5) Pretraga naslova/tijela sa LIKE
        """
        SELECT TOP (100) p.Id, p.Title, p.Score, p.CreationDate
        FROM dbo.Posts_Test p
        WHERE p.PostTypeId = 1
          AND (p.Title LIKE '%sql server%' OR p.Body LIKE '%index%')
        ORDER BY p.Score DESC, p.CreationDate DESC;
        """,

        # 6) Latest activity feed (JOIN posts/users/comments)
        """
        SELECT TOP (200) c.CreationDate AS ActivityDate, p.Id AS PostId, u.DisplayName, c.Score AS CommentScore
        FROM dbo.Comments c
        JOIN dbo.Posts_Test p ON p.Id = c.PostId
        JOIN dbo.Users u ON u.Id = c.UserId
        ORDER BY c.CreationDate DESC;
        """,

        # 7) Insert test komentar (DML)
        "INSERT INTO dbo.Comments (PostId, Score, Text, CreationDate, UserId) VALUES (1, 0, 'Test komentar', GETDATE(), 2);",

        # 8) Update Posts_Test
        "UPDATE dbo.Posts_Test SET Score = Score + 1 WHERE Id < 1000;",

        # 9) Delete iz Comments
        "DELETE FROM dbo.Comments WHERE Id < 1000;"
    ],

    "indexes": [],      # može se koristiti baseline
    "columnstore": [],
    "compression": [],
    "partition": [
        # workload nad particionisanom tabelom
        """
        SELECT Godina, COUNT(*) AS BrojPostova
        FROM dbo.Posts_TestPartitioned
        GROUP BY Godina
        ORDER BY Godina;
        """
    ]
}


