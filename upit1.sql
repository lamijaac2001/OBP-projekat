/* ================================
   0. KREIRANJE TEST TABELE
   ================================ */
IF OBJECT_ID('dbo.Posts_Test', 'U') IS NOT NULL
    DROP TABLE dbo.Posts_Test;

SELECT TOP 200000 *
INTO dbo.Posts_Test
FROM dbo.Posts;


/* ================================
   1. WORKLOAD – ANALITIČKI UPITI
   ================================ */

-- A1) Top autori po skoru odgovora u zadnjih 5 godina
-- Vraća top 50 korisnika sa zbirnim score-om za odgovore
-- Bez rizika da filter na datum izbaci sve redove
SELECT TOP (50) 
    u.Id, 
    u.DisplayName, 
    SUM(p.Score) AS TotalAnswerScore,
    COUNT(p.Id) AS NumAnswers,
    MIN(p.CreationDate) AS FirstAnswerDate,
    MAX(p.CreationDate) AS LastAnswerDate
FROM dbo.Posts_Test p
JOIN dbo.Users u ON u.Id = p.OwnerUserId
WHERE p.PostTypeId = 2  -- samo odgovori

GROUP BY u.Id, u.DisplayName
ORDER BY TotalAnswerScore DESC;




-- A2) Trend broja pitanja po mjesecu i tagu
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




-- A3) Ko-pojavljivanje tagova (top 100 parova)
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
     AND pt1.TagName < pt2.TagName  -- izbjegava duplikate i samopojavljivanje
)
SELECT TOP (100)
    TagA, TagB, COUNT(*) AS PairCount
FROM TagPairs
GROUP BY TagA, TagB
ORDER BY PairCount DESC;




/* ================================
   2. WORKLOAD – TRANSAKCIJSKI UPITI
   ================================ */

-- T1) Lookup posta + accepted answer
-- Lookup svih pitanja sa prihvaćenim odgovorom
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
WHERE q.PostTypeId = 1  -- samo pitanja
ORDER BY q.CreationDate DESC;


-- T2) Pretraga naslova/tijela sa LIKE
SELECT TOP (100) p.Id, p.Title, p.Score, p.CreationDate
FROM dbo.Posts_Test p
WHERE p.PostTypeId = 1
  AND (p.Title LIKE '%sql server%' OR p.Body LIKE '%index%')
ORDER BY p.Score DESC, p.CreationDate DESC;

-- T3) Latest activity feed (JOIN posts/users/comments)
SELECT TOP (200) c.CreationDate AS ActivityDate, p.Id AS PostId, u.DisplayName, c.Score AS CommentScore
FROM dbo.Comments c
JOIN dbo.Posts_Test p ON p.Id = c.PostId
JOIN dbo.Users u ON u.Id = c.UserId
ORDER BY c.CreationDate DESC;

-- T4) Insert u Comments
INSERT INTO dbo.Comments (PostId, Score, Text, CreationDate, UserId)
VALUES (1, 0, 'Test komentar', GETDATE(), 2);

-- T5) Update u Posts_Test
UPDATE dbo.Posts_Test
SET Score = Score + 1
WHERE Id < 1000;

-- T6) Delete iz Comments
DELETE FROM dbo.Comments
WHERE Id < 1000;


/* ================================
   3. OPTIMIZACIJE
   ================================ */

-- Indeksi
CREATE NONCLUSTERED INDEX IX_PostsTest_CreationDate 
ON dbo.Posts_Test(CreationDate);

CREATE NONCLUSTERED INDEX IX_PostsTest_OwnerUserId 
ON dbo.Posts_Test(OwnerUserId);

-- Columnstore
CREATE CLUSTERED COLUMNSTORE INDEX CCI_PostsTest 
ON dbo.Posts_Test;

-- Kompresija
ALTER INDEX ALL ON dbo.Posts_Test 
REBUILD WITH (DATA_COMPRESSION = PAGE);


/* ================================
   4. PARTICIONISANJE
   ================================ */

IF OBJECT_ID('dbo.Posts_TestPartitioned', 'U') IS NOT NULL
    DROP TABLE dbo.Posts_TestPartitioned;

IF EXISTS (SELECT * FROM sys.partition_functions WHERE name = 'pfYear')
    DROP PARTITION FUNCTION pfYear;
CREATE PARTITION FUNCTION pfYear (INT)
AS RANGE LEFT FOR VALUES (2010, 2015, 2020);

IF EXISTS (SELECT * FROM sys.partition_schemes WHERE name = 'psYear')
    DROP PARTITION SCHEME psYear;
CREATE PARTITION SCHEME psYear
AS PARTITION pfYear ALL TO ([PRIMARY]);

CREATE TABLE dbo.Posts_TestPartitioned (
    Id INT NOT NULL,
    OwnerUserId INT,
    CreationDate DATETIME,
    Godina AS YEAR(CreationDate) PERSISTED,
    Score INT,
    CONSTRAINT PK_PostsTestPartitioned PRIMARY KEY (Godina, Id)
) ON psYear(Godina);

INSERT INTO dbo.Posts_TestPartitioned (Id, OwnerUserId, CreationDate, Score)
SELECT TOP 50000 Id, OwnerUserId, CreationDate, Score
FROM dbo.Posts;

