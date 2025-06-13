-- Query to list racer data with their preliminary round race schedules
-- Shows pinny, name, class, and up to 3 races in format "heat:lane"

SELECT 
    r.carnumber as pinny,
    r.firstname,
    r.lastname,
    c.class as classname,
    MAX(CASE WHEN race_num = 1 THEN heat || ':' || lane END) as race1,
    MAX(CASE WHEN race_num = 2 THEN heat || ':' || lane END) as race2,
    MAX(CASE WHEN race_num = 3 THEN heat || ':' || lane END) as race3
FROM RegistrationInfo r
INNER JOIN Classes c ON r.classid = c.classid
INNER JOIN (
    SELECT 
        rc.racerid,
        rc.heat,
        rc.lane,
        ROW_NUMBER() OVER (PARTITION BY rc.racerid ORDER BY rc.heat) as race_num
    FROM RaceChart rc
    INNER JOIN Rounds rd ON rc.roundid = rd.roundid
    WHERE rd.roundname LIKE '%Preliminary%' OR rd.roundname = '1 Preliminary'
) races ON r.racerid = races.racerid
GROUP BY r.racerid, r.carnumber, r.firstname, r.lastname, c.class
ORDER BY c.class, r.lastname, r.firstname;