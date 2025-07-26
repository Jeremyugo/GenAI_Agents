# SQL Agent 

This dir contains code for building an SQL agent that connects to a relational database and answers questions using data from the SQL database.

The Agent can:
1. List all tables in the database
2. Decide which tables are relevant to the query
3. Fetch table Schemas
4. Generate a query to answer the user's question using
5. Check its generated query for errors
6. Execute the query
7. Provide a response based on the results

## SQL Agent - Result


```markdown
================================ Human Message =================================

Which genre on average has the longest tracks?

================================== Ai Message ==================================
Tool Calls:
  list_tables (call_p4TYzu7f1Ae44M7FKKaHNOC0)
 Call ID: call_p4TYzu7f1Ae44M7FKKaHNOC0
  Args:
    state: {'messages': []}

================================= Tool Message =================================
Name: list_tables

Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track

================================== Ai Message ==================================
Tool Calls:
  get_schema (call_lrFLOUqMjVUC8fSxDMoGanr7)
 Call ID: call_lrFLOUqMjVUC8fSxDMoGanr7
  Args:
    list_of_tables: Genre
  get_schema (call_cKnuCqquBjeSz8cLsiM9Q7UJ)
 Call ID: call_cKnuCqquBjeSz8cLsiM9Q7UJ
  Args:
    list_of_tables: Track

================================= Tool Message =================================
Name: get_schema

CREATE TABLE "Track" (
        "TrackId" BIGINT, 
        "Name" TEXT, 
        "AlbumId" BIGINT, 
        "MediaTypeId" BIGINT, 
        "GenreId" BIGINT, 
        "Composer" TEXT, 
        "Milliseconds" BIGINT, 
        "Bytes" BIGINT, 
        "UnitPrice" DOUBLE PRECISION
)

/*
3 rows from Track table:
TrackId Name    AlbumId MediaTypeId     GenreId Composer        Milliseconds    Bytes   UnitPrice
1       For Those About To Rock (We Salute You) 1       1       1       Angus Young, Malcolm Young, Brian Johnson       343719  11170334        0.99
2       Balls to the Wall       2       2       1       None    342562  5510424 0.99
3       Fast As a Shark 3       2       1       F. Baltes, S. Kaufman, U. Dirkscneider & W. Hoffman     230619  3990994 0.99
*/

================================== Ai Message ==================================
Tool Calls:
  execute_verified_query (call_3bHPqmpXjodvfGTLAn9QkNZ8)
 Call ID: call_3bHPqmpXjodvfGTLAn9QkNZ8
  Args:
    sql_query_to_execute: SELECT g.Name AS Genre, AVG(t.Milliseconds) AS Avg_Track_Length
FROM Genre g
JOIN Track t ON g.GenreId = t.GenreId
GROUP BY g.Name
ORDER BY Avg_Track_Length DESC;

================================= Tool Message =================================
Name: execute_verified_query

Error: (psycopg2.errors.UndefinedTable) relation "genre" does not exist
LINE 2: FROM Genre g
             ^

[SQL: SELECT g.Name AS Genre, AVG(t.Milliseconds) AS Avg_Track_Length
FROM Genre g
JOIN Track t ON g.GenreId = t.GenreId
GROUP BY g.Name
ORDER BY Avg_Track_Length DESC;]
(Background on this error at: https://sqlalche.me/e/20/f405)

================================== Ai Message ==================================

It seems there was an error in the query, let me correct it and try again.
Tool Calls:
  execute_verified_query (call_HXBsfVlmlpU6NnUWpLVgIpVR)
 Call ID: call_HXBsfVlmlpU6NnUWpLVgIpVR
  Args:
    sql_query_to_execute: SELECT g."Name" AS Genre, AVG(t."Milliseconds") AS Avg_Track_Length
FROM "Genre" g
JOIN "Track" t ON g."GenreId" = t."GenreId"
GROUP BY g."Name"
ORDER BY Avg_Track_Length DESC;

================================= Tool Message =================================
Name: execute_verified_query

[('Sci Fi & Fantasy', Decimal('2911783.038461538462')), ('Science Fiction', Decimal('2625549.076923076923')), ('Drama', Decimal('2575283.781250000000')), ('TV Shows', Decimal('2145041.021505376344')), ('Comedy', Decimal('1585263.705882352941')), ('Metal', Decimal('309749.443850267380')), ('Electronica/Dance', Decimal('302985.800000000000')), ('Heavy Metal', Decimal('297452.928571428571')), ('Classical', Decimal('293867.567567567568')), ('Jazz', Decimal('291755.376923076923')), ('Rock', Decimal('283910.043176561295')), ('Blues', Decimal('270359.777777777778')), ('Alternative', Decimal('264058.525000000000')), ('Reggae', Decimal('247177.758620689655')), ('Soundtrack', Decimal('244370.883720930233')), ('Alternative & Punk', Decimal('234353.849397590361')), ('Latin', Decimal('232859.262521588946')), ('Pop', Decimal('229034.104166666667')), ('World', Decimal('224923.821428571429')), ('R&B/Soul', Decimal('220066.852459016393')), ('Bossa Nova', Decimal('219590.000000000000')), ('Easy Listening', Decimal('189164.208333333333')), ('Hip Hop/Rap', Decimal('178176.285714285714')), ('Opera', Decimal('174813.000000000000')), ('Rock And Roll', Decimal('134643.500000000000'))]

================================== Ai Message ==================================

The genre "Sci Fi & Fantasy" on average has the longest tracks with an average track length of approximately 2,911,783 milliseconds.
```
