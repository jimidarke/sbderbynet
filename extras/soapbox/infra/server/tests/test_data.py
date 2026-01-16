"""
Test Data for DerbyNet Server Tests

This module contains normalized test data extracted from a real DerbyNet database.
Data is structured to be inserted programmatically, allowing tests to choose
their desired database state:

- CLASSES: 3 age-based classes (6-8, 9-11, 12-14)
- RANKS: One rank per class
- RACERS: 107 racers with realistic names
- ROUNDS: 11 rounds including preliminary through finals
- RACE_RESULTS: 102 completed heats with finish times

Usage in fixtures:
    from test_data import CLASSES, RACERS, ROUNDS, RACE_RESULTS

    # Insert only what the test needs
    for cls in CLASSES:
        cursor.execute("INSERT INTO Classes ...")
"""

# Classes - 3 age groups for soapbox derby
CLASSES = [
    {"classid": 1, "class": "Ages 6-8", "sortorder": 1},
    {"classid": 2, "class": "Ages 9-11", "sortorder": 2},
    {"classid": 3, "class": "Ages 12-14", "sortorder": 3},
]

# Ranks - One rank per class (simplified for soapbox derby)
RANKS = [
    {"rankid": 1, "rank": "Ages 6-8", "classid": 1, "sortorder": 1},
    {"rankid": 2, "rank": "Ages 9-11", "classid": 2, "sortorder": 1},
    {"rankid": 3, "rank": "Ages 12-14", "classid": 3, "sortorder": 1},
]

# Racers - 107 racers with realistic names
# Class 1 (Ages 6-8): carnumbers 1-34, racerids 1-34
# Class 2 (Ages 9-11): carnumbers 101-136, racerids 35-70
# Class 3 (Ages 12-14): carnumbers 201-237, racerids 71-107
RACERS = [
    # Class 1: Ages 6-8 (34 racers)
    {"racerid": 1, "carnumber": 1, "firstname": "Jared", "lastname": "Perez", "classid": 1, "rankid": 1},
    {"racerid": 2, "carnumber": 2, "firstname": "Emmie", "lastname": "Eslick", "classid": 1, "rankid": 1},
    {"racerid": 3, "carnumber": 3, "firstname": "Mason", "lastname": "Melia", "classid": 1, "rankid": 1},
    {"racerid": 4, "carnumber": 4, "firstname": "Deshawn", "lastname": "Farmer", "classid": 1, "rankid": 1},
    {"racerid": 5, "carnumber": 5, "firstname": "Candi", "lastname": "Coil", "classid": 1, "rankid": 1},
    {"racerid": 6, "carnumber": 6, "firstname": "Jeanie", "lastname": "Jackson", "classid": 1, "rankid": 1},
    {"racerid": 7, "carnumber": 7, "firstname": "Emilia", "lastname": "Everett", "classid": 1, "rankid": 1},
    {"racerid": 8, "carnumber": 8, "firstname": "Christian", "lastname": "Sweeney", "classid": 1, "rankid": 1},
    {"racerid": 9, "carnumber": 9, "firstname": "Stephen", "lastname": "Johnson", "classid": 1, "rankid": 1},
    {"racerid": 10, "carnumber": 10, "firstname": "Melisa", "lastname": "McGrath", "classid": 1, "rankid": 1},
    {"racerid": 11, "carnumber": 11, "firstname": "Waldo", "lastname": "Anderson", "classid": 1, "rankid": 1},
    {"racerid": 12, "carnumber": 12, "firstname": "Moshe", "lastname": "Burnett", "classid": 1, "rankid": 1},
    {"racerid": 13, "carnumber": 13, "firstname": "Ladonna", "lastname": "Gross", "classid": 1, "rankid": 1},
    {"racerid": 14, "carnumber": 14, "firstname": "Arletta", "lastname": "Allison", "classid": 1, "rankid": 1},
    {"racerid": 15, "carnumber": 15, "firstname": "Clare", "lastname": "Gregory", "classid": 1, "rankid": 1},
    {"racerid": 16, "carnumber": 16, "firstname": "Kendrick", "lastname": "Ramsey", "classid": 1, "rankid": 1},
    {"racerid": 17, "carnumber": 17, "firstname": "Lorinda", "lastname": "Lansford", "classid": 1, "rankid": 1},
    {"racerid": 18, "carnumber": 18, "firstname": "Garland", "lastname": "Gerlach", "classid": 1, "rankid": 1},
    {"racerid": 19, "carnumber": 19, "firstname": "Hildegard", "lastname": "Harlin", "classid": 1, "rankid": 1},
    {"racerid": 20, "carnumber": 20, "firstname": "Faustino", "lastname": "Holmes", "classid": 1, "rankid": 1},
    {"racerid": 21, "carnumber": 21, "firstname": "Sasha", "lastname": "Glass", "classid": 1, "rankid": 1},
    {"racerid": 22, "carnumber": 22, "firstname": "Jamison", "lastname": "Morales", "classid": 1, "rankid": 1},
    {"racerid": 23, "carnumber": 23, "firstname": "Eloise", "lastname": "Ellwood", "classid": 1, "rankid": 1},
    {"racerid": 24, "carnumber": 24, "firstname": "Violet", "lastname": "Gonzales", "classid": 1, "rankid": 1},
    {"racerid": 25, "carnumber": 25, "firstname": "Dawn", "lastname": "Levy", "classid": 1, "rankid": 1},
    {"racerid": 26, "carnumber": 26, "firstname": "Octavio", "lastname": "Hayden", "classid": 1, "rankid": 1},
    {"racerid": 27, "carnumber": 27, "firstname": "Otha", "lastname": "Moss", "classid": 1, "rankid": 1},
    {"racerid": 28, "carnumber": 28, "firstname": "Gwendolyn", "lastname": "Moore", "classid": 1, "rankid": 1},
    {"racerid": 29, "carnumber": 29, "firstname": "Julia", "lastname": "Murillo", "classid": 1, "rankid": 1},
    {"racerid": 30, "carnumber": 30, "firstname": "Major", "lastname": "McCormick", "classid": 1, "rankid": 1},
    {"racerid": 31, "carnumber": 31, "firstname": "Nelia", "lastname": "Newcombe", "classid": 1, "rankid": 1},
    {"racerid": 32, "carnumber": 32, "firstname": "Meghann", "lastname": "Martens", "classid": 1, "rankid": 1},
    {"racerid": 33, "carnumber": 33, "firstname": "Janet", "lastname": "Molina", "classid": 1, "rankid": 1},
    {"racerid": 34, "carnumber": 34, "firstname": "Conrad", "lastname": "Roy", "classid": 1, "rankid": 1},
    # Class 2: Ages 9-11 (36 racers)
    {"racerid": 35, "carnumber": 101, "firstname": "Jared", "lastname": "McDaniel", "classid": 2, "rankid": 2},
    {"racerid": 36, "carnumber": 102, "firstname": "Camille", "lastname": "Montes", "classid": 2, "rankid": 2},
    {"racerid": 37, "carnumber": 103, "firstname": "Tiera", "lastname": "Timbers", "classid": 2, "rankid": 2},
    {"racerid": 38, "carnumber": 104, "firstname": "Jasper", "lastname": "Berger", "classid": 2, "rankid": 2},
    {"racerid": 39, "carnumber": 105, "firstname": "Tameka", "lastname": "Harmon", "classid": 2, "rankid": 2},
    {"racerid": 40, "carnumber": 106, "firstname": "Gerry", "lastname": "Becker", "classid": 2, "rankid": 2},
    {"racerid": 41, "carnumber": 107, "firstname": "Kenia", "lastname": "Kung", "classid": 2, "rankid": 2},
    {"racerid": 42, "carnumber": 108, "firstname": "Cristobal", "lastname": "George", "classid": 2, "rankid": 2},
    {"racerid": 43, "carnumber": 109, "firstname": "Callie", "lastname": "Lowery", "classid": 2, "rankid": 2},
    {"racerid": 44, "carnumber": 110, "firstname": "Marlene", "lastname": "McDaniel", "classid": 2, "rankid": 2},
    {"racerid": 45, "carnumber": 111, "firstname": "Eileen", "lastname": "Wilcox", "classid": 2, "rankid": 2},
    {"racerid": 46, "carnumber": 112, "firstname": "Rochelle", "lastname": "Ruddell", "classid": 2, "rankid": 2},
    {"racerid": 47, "carnumber": 113, "firstname": "Barry", "lastname": "Turner", "classid": 2, "rankid": 2},
    {"racerid": 48, "carnumber": 114, "firstname": "Lupe", "lastname": "Kent", "classid": 2, "rankid": 2},
    {"racerid": 49, "carnumber": 115, "firstname": "Adrianna", "lastname": "Armendariz", "classid": 2, "rankid": 2},
    {"racerid": 50, "carnumber": 116, "firstname": "Palmer", "lastname": "Mejia", "classid": 2, "rankid": 2},
    {"racerid": 51, "carnumber": 117, "firstname": "Mario", "lastname": "Hays", "classid": 2, "rankid": 2},
    {"racerid": 52, "carnumber": 118, "firstname": "Josefine", "lastname": "Jensen", "classid": 2, "rankid": 2},
    {"racerid": 53, "carnumber": 119, "firstname": "Quinton", "lastname": "Gaines", "classid": 2, "rankid": 2},
    {"racerid": 54, "carnumber": 120, "firstname": "Marcellus", "lastname": "Buchanan", "classid": 2, "rankid": 2},
    {"racerid": 55, "carnumber": 121, "firstname": "Adam", "lastname": "Stewart", "classid": 2, "rankid": 2},
    {"racerid": 56, "carnumber": 122, "firstname": "Normand", "lastname": "Hess", "classid": 2, "rankid": 2},
    {"racerid": 57, "carnumber": 123, "firstname": "Mack", "lastname": "Alvarez", "classid": 2, "rankid": 2},
    {"racerid": 58, "carnumber": 124, "firstname": "Gregg", "lastname": "Garofalo", "classid": 2, "rankid": 2},
    {"racerid": 59, "carnumber": 125, "firstname": "Sylvia", "lastname": "Turner", "classid": 2, "rankid": 2},
    {"racerid": 60, "carnumber": 126, "firstname": "Joseph", "lastname": "Judkins", "classid": 2, "rankid": 2},
    {"racerid": 61, "carnumber": 127, "firstname": "Albertine", "lastname": "Alto", "classid": 2, "rankid": 2},
    {"racerid": 62, "carnumber": 128, "firstname": "Theresa", "lastname": "Trabue", "classid": 2, "rankid": 2},
    {"racerid": 63, "carnumber": 129, "firstname": "Al", "lastname": "McIntosh", "classid": 2, "rankid": 2},
    {"racerid": 64, "carnumber": 130, "firstname": "Jackson", "lastname": "Schneider", "classid": 2, "rankid": 2},
    {"racerid": 65, "carnumber": 131, "firstname": "Rod", "lastname": "Ferrell", "classid": 2, "rankid": 2},
    {"racerid": 66, "carnumber": 132, "firstname": "Junko", "lastname": "Johannes", "classid": 2, "rankid": 2},
    {"racerid": 67, "carnumber": 133, "firstname": "Hoyt", "lastname": "Mullins", "classid": 2, "rankid": 2},
    {"racerid": 68, "carnumber": 134, "firstname": "Shannon", "lastname": "Romero", "classid": 2, "rankid": 2},
    {"racerid": 69, "carnumber": 135, "firstname": "Charis", "lastname": "Cormack", "classid": 2, "rankid": 2},
    {"racerid": 70, "carnumber": 136, "firstname": "Amanda", "lastname": "Guzman", "classid": 2, "rankid": 2},
    # Class 3: Ages 12-14 (37 racers)
    {"racerid": 71, "carnumber": 201, "firstname": "Brigitte", "lastname": "Potts", "classid": 3, "rankid": 3},
    {"racerid": 72, "carnumber": 202, "firstname": "Quiana", "lastname": "Qualls", "classid": 3, "rankid": 3},
    {"racerid": 73, "carnumber": 203, "firstname": "Isabel", "lastname": "Rojas", "classid": 3, "rankid": 3},
    {"racerid": 74, "carnumber": 204, "firstname": "Jewel", "lastname": "Allison", "classid": 3, "rankid": 3},
    {"racerid": 75, "carnumber": 205, "firstname": "Lavern", "lastname": "Lackey", "classid": 3, "rankid": 3},
    {"racerid": 76, "carnumber": 206, "firstname": "Kandace", "lastname": "Kohn", "classid": 3, "rankid": 3},
    {"racerid": 77, "carnumber": 207, "firstname": "Santos", "lastname": "Phillips", "classid": 3, "rankid": 3},
    {"racerid": 78, "carnumber": 208, "firstname": "Derrick", "lastname": "Fields", "classid": 3, "rankid": 3},
    {"racerid": 79, "carnumber": 209, "firstname": "Aimee", "lastname": "Logan", "classid": 3, "rankid": 3},
    {"racerid": 80, "carnumber": 210, "firstname": "Giselle", "lastname": "Galley", "classid": 3, "rankid": 3},
    {"racerid": 81, "carnumber": 211, "firstname": "Dwight", "lastname": "Doman", "classid": 3, "rankid": 3},
    {"racerid": 82, "carnumber": 212, "firstname": "Terri", "lastname": "Herring", "classid": 3, "rankid": 3},
    {"racerid": 83, "carnumber": 213, "firstname": "Armida", "lastname": "Archuleta", "classid": 3, "rankid": 3},
    {"racerid": 84, "carnumber": 214, "firstname": "Pam", "lastname": "Cisneros", "classid": 3, "rankid": 3},
    {"racerid": 85, "carnumber": 215, "firstname": "Millie", "lastname": "Munsell", "classid": 3, "rankid": 3},
    {"racerid": 86, "carnumber": 216, "firstname": "Yelena", "lastname": "Yarborough", "classid": 3, "rankid": 3},
    {"racerid": 87, "carnumber": 217, "firstname": "Celia", "lastname": "Ford", "classid": 3, "rankid": 3},
    {"racerid": 88, "carnumber": 218, "firstname": "Loyd", "lastname": "Spears", "classid": 3, "rankid": 3},
    {"racerid": 89, "carnumber": 219, "firstname": "Edna", "lastname": "Essary", "classid": 3, "rankid": 3},
    {"racerid": 90, "carnumber": 220, "firstname": "Shelia", "lastname": "Pearson", "classid": 3, "rankid": 3},
    {"racerid": 91, "carnumber": 221, "firstname": "Anabel", "lastname": "Antos", "classid": 3, "rankid": 3},
    {"racerid": 92, "carnumber": 222, "firstname": "Courtney", "lastname": "Rivers", "classid": 3, "rankid": 3},
    {"racerid": 93, "carnumber": 223, "firstname": "Tabitha", "lastname": "Blackwell", "classid": 3, "rankid": 3},
    {"racerid": 94, "carnumber": 224, "firstname": "Fredrick", "lastname": "Chaney", "classid": 3, "rankid": 3},
    {"racerid": 95, "carnumber": 225, "firstname": "Stanton", "lastname": "Sayegh", "classid": 3, "rankid": 3},
    {"racerid": 96, "carnumber": 226, "firstname": "Sarah", "lastname": "Thompson", "classid": 3, "rankid": 3},
    {"racerid": 97, "carnumber": 227, "firstname": "Ross", "lastname": "Schmitt", "classid": 3, "rankid": 3},
    {"racerid": 98, "carnumber": 228, "firstname": "Terrence", "lastname": "Bates", "classid": 3, "rankid": 3},
    {"racerid": 99, "carnumber": 229, "firstname": "Marta", "lastname": "Wilkinson", "classid": 3, "rankid": 3},
    {"racerid": 100, "carnumber": 230, "firstname": "Darren", "lastname": "Stuart", "classid": 3, "rankid": 3},
    {"racerid": 101, "carnumber": 231, "firstname": "Angelia", "lastname": "Richardson", "classid": 3, "rankid": 3},
    {"racerid": 102, "carnumber": 232, "firstname": "Herman", "lastname": "Morrison", "classid": 3, "rankid": 3},
    {"racerid": 103, "carnumber": 233, "firstname": "Randolph", "lastname": "Radabaugh", "classid": 3, "rankid": 3},
    {"racerid": 104, "carnumber": 234, "firstname": "Tanya", "lastname": "Tilford", "classid": 3, "rankid": 3},
    {"racerid": 105, "carnumber": 235, "firstname": "Rubye", "lastname": "Raymo", "classid": 3, "rankid": 3},
    {"racerid": 106, "carnumber": 236, "firstname": "Roderick", "lastname": "Weiss", "classid": 3, "rankid": 3},
    {"racerid": 107, "carnumber": 237, "firstname": "Monica", "lastname": "Castillo", "classid": 3, "rankid": 3},
]

# Rounds - 11 rounds including preliminary through finals
# Each class progresses: Preliminary -> Quarter Finals -> Semi-Finals -> Finals
ROUNDS = [
    {"roundid": 1, "classid": 1, "round": 1, "roundname": "1 Preliminary"},
    {"roundid": 2, "classid": 2, "round": 1, "roundname": "1 Preliminary"},
    {"roundid": 3, "classid": 3, "round": 1, "roundname": "1 Preliminary"},
    {"roundid": 4, "classid": 3, "round": 2, "roundname": "2 Semi-Finals"},
    {"roundid": 5, "classid": 3, "round": 3, "roundname": "3 Finals"},
    {"roundid": 6, "classid": 2, "round": 2, "roundname": "2 Quarter Finals"},
    {"roundid": 7, "classid": 2, "round": 3, "roundname": "3 Semi-Finals"},
    {"roundid": 8, "classid": 2, "round": 4, "roundname": "4 Finals"},
    {"roundid": 9, "classid": 1, "round": 2, "roundname": "2 Quarter Finals"},
    {"roundid": 10, "classid": 1, "round": 3, "roundname": "3 Semi-Finals"},
    {"roundid": 11, "classid": 1, "round": 4, "roundname": "4 Finals"},
]

# Race Results - 102 completed heats from Round 1 (Preliminary) for Class 1
# 3-lane track, finish times in seconds (realistic 4.5-8.5 second range)
RACE_RESULTS = [
    {"resultid": 1, "roundid": 1, "heat": 1, "lane": 1, "racerid": 16, "finishtime": 7.274, "finishplace": 3},
    {"resultid": 2, "roundid": 1, "heat": 1, "lane": 2, "racerid": 24, "finishtime": 5.943, "finishplace": 2},
    {"resultid": 3, "roundid": 1, "heat": 1, "lane": 3, "racerid": 15, "finishtime": 5.386, "finishplace": 1},
    {"resultid": 4, "roundid": 1, "heat": 2, "lane": 1, "racerid": 19, "finishtime": 6.453, "finishplace": 1},
    {"resultid": 5, "roundid": 1, "heat": 2, "lane": 2, "racerid": 31, "finishtime": 7.122, "finishplace": 2},
    {"resultid": 6, "roundid": 1, "heat": 2, "lane": 3, "racerid": 22, "finishtime": 7.46, "finishplace": 3},
    {"resultid": 7, "roundid": 1, "heat": 3, "lane": 1, "racerid": 30, "finishtime": 5.924, "finishplace": 2},
    {"resultid": 8, "roundid": 1, "heat": 3, "lane": 2, "racerid": 27, "finishtime": 6.62, "finishplace": 3},
    {"resultid": 9, "roundid": 1, "heat": 3, "lane": 3, "racerid": 21, "finishtime": 5.324, "finishplace": 1},
    {"resultid": 10, "roundid": 1, "heat": 4, "lane": 1, "racerid": 23, "finishtime": 6.911, "finishplace": 2},
    {"resultid": 11, "roundid": 1, "heat": 4, "lane": 2, "racerid": 32, "finishtime": 7.416, "finishplace": 3},
    {"resultid": 12, "roundid": 1, "heat": 4, "lane": 3, "racerid": 11, "finishtime": 5.591, "finishplace": 1},
    {"resultid": 13, "roundid": 1, "heat": 5, "lane": 1, "racerid": 4, "finishtime": 7.229, "finishplace": 3},
    {"resultid": 14, "roundid": 1, "heat": 5, "lane": 2, "racerid": 34, "finishtime": 5.294, "finishplace": 1},
    {"resultid": 15, "roundid": 1, "heat": 5, "lane": 3, "racerid": 1, "finishtime": 6.75, "finishplace": 2},
    {"resultid": 16, "roundid": 1, "heat": 6, "lane": 1, "racerid": 29, "finishtime": 7.457, "finishplace": 2},
    {"resultid": 17, "roundid": 1, "heat": 6, "lane": 2, "racerid": 17, "finishtime": 7.691, "finishplace": 3},
    {"resultid": 18, "roundid": 1, "heat": 6, "lane": 3, "racerid": 5, "finishtime": 6.078, "finishplace": 1},
    {"resultid": 19, "roundid": 1, "heat": 7, "lane": 1, "racerid": 3, "finishtime": 6.032, "finishplace": 1},
    {"resultid": 20, "roundid": 1, "heat": 7, "lane": 2, "racerid": 20, "finishtime": 7.224, "finishplace": 3},
    {"resultid": 21, "roundid": 1, "heat": 7, "lane": 3, "racerid": 33, "finishtime": 6.789, "finishplace": 2},
    {"resultid": 22, "roundid": 1, "heat": 8, "lane": 1, "racerid": 14, "finishtime": 4.708, "finishplace": 1},
    {"resultid": 23, "roundid": 1, "heat": 8, "lane": 2, "racerid": 26, "finishtime": 6.569, "finishplace": 3},
    {"resultid": 24, "roundid": 1, "heat": 8, "lane": 3, "racerid": 18, "finishtime": 5.959, "finishplace": 2},
    {"resultid": 25, "roundid": 1, "heat": 9, "lane": 1, "racerid": 8, "finishtime": 7.373, "finishplace": 2},
    {"resultid": 26, "roundid": 1, "heat": 9, "lane": 2, "racerid": 33, "finishtime": 7.456, "finishplace": 3},
    {"resultid": 27, "roundid": 1, "heat": 9, "lane": 3, "racerid": 28, "finishtime": 5.832, "finishplace": 1},
    {"resultid": 28, "roundid": 1, "heat": 10, "lane": 1, "racerid": 7, "finishtime": 6.15, "finishplace": 1},
    {"resultid": 29, "roundid": 1, "heat": 10, "lane": 2, "racerid": 6, "finishtime": 7.81, "finishplace": 3},
    {"resultid": 30, "roundid": 1, "heat": 10, "lane": 3, "racerid": 24, "finishtime": 7.663, "finishplace": 2},
    {"resultid": 31, "roundid": 1, "heat": 11, "lane": 1, "racerid": 25, "finishtime": 6.363, "finishplace": 2},
    {"resultid": 32, "roundid": 1, "heat": 11, "lane": 2, "racerid": 15, "finishtime": 4.678, "finishplace": 1},
    {"resultid": 33, "roundid": 1, "heat": 11, "lane": 3, "racerid": 23, "finishtime": 6.464, "finishplace": 3},
    {"resultid": 34, "roundid": 1, "heat": 12, "lane": 1, "racerid": 13, "finishtime": 5.596, "finishplace": 1},
    {"resultid": 35, "roundid": 1, "heat": 12, "lane": 2, "racerid": 18, "finishtime": 6.278, "finishplace": 2},
    {"resultid": 36, "roundid": 1, "heat": 12, "lane": 3, "racerid": 31, "finishtime": 6.398, "finishplace": 3},
    {"resultid": 37, "roundid": 1, "heat": 13, "lane": 1, "racerid": 34, "finishtime": 6.93, "finishplace": 2},
    {"resultid": 38, "roundid": 1, "heat": 13, "lane": 2, "racerid": 29, "finishtime": 5.59, "finishplace": 1},
    {"resultid": 39, "roundid": 1, "heat": 13, "lane": 3, "racerid": 2, "finishtime": 7.5, "finishplace": 3},
    {"resultid": 40, "roundid": 1, "heat": 14, "lane": 1, "racerid": 12, "finishtime": 7.115, "finishplace": 3},
    {"resultid": 41, "roundid": 1, "heat": 14, "lane": 2, "racerid": 21, "finishtime": 6.723, "finishplace": 2},
    {"resultid": 42, "roundid": 1, "heat": 14, "lane": 3, "racerid": 4, "finishtime": 6.187, "finishplace": 1},
    {"resultid": 43, "roundid": 1, "heat": 15, "lane": 1, "racerid": 11, "finishtime": 5.968, "finishplace": 2},
    {"resultid": 44, "roundid": 1, "heat": 15, "lane": 2, "racerid": 10, "finishtime": 6.731, "finishplace": 3},
    {"resultid": 45, "roundid": 1, "heat": 15, "lane": 3, "racerid": 17, "finishtime": 5.618, "finishplace": 1},
    {"resultid": 46, "roundid": 1, "heat": 16, "lane": 1, "racerid": 27, "finishtime": 6.381, "finishplace": 2},
    {"resultid": 47, "roundid": 1, "heat": 16, "lane": 2, "racerid": 23, "finishtime": 5.317, "finishplace": 1},
    {"resultid": 48, "roundid": 1, "heat": 16, "lane": 3, "racerid": 9, "finishtime": 7.184, "finishplace": 3},
    {"resultid": 49, "roundid": 1, "heat": 17, "lane": 1, "racerid": 10, "finishtime": 5.866, "finishplace": 3},
    {"resultid": 50, "roundid": 1, "heat": 17, "lane": 2, "racerid": 1, "finishtime": 5.796, "finishplace": 2},
    {"resultid": 51, "roundid": 1, "heat": 17, "lane": 3, "racerid": 3, "finishtime": 5.231, "finishplace": 1},
    {"resultid": 52, "roundid": 1, "heat": 18, "lane": 1, "racerid": 2, "finishtime": 7.783, "finishplace": 2},
    {"resultid": 53, "roundid": 1, "heat": 18, "lane": 2, "racerid": 5, "finishtime": 6.218, "finishplace": 1},
    {"resultid": 54, "roundid": 1, "heat": 18, "lane": 3, "racerid": 14, "finishtime": 8.12, "finishplace": 3},
    {"resultid": 55, "roundid": 1, "heat": 19, "lane": 1, "racerid": 26, "finishtime": 7.085, "finishplace": 3},
    {"resultid": 56, "roundid": 1, "heat": 19, "lane": 2, "racerid": 28, "finishtime": 6.297, "finishplace": 1},
    {"resultid": 57, "roundid": 1, "heat": 19, "lane": 3, "racerid": 7, "finishtime": 6.972, "finishplace": 2},
    {"resultid": 58, "roundid": 1, "heat": 20, "lane": 1, "racerid": 6, "finishtime": 5.777, "finishplace": 2},
    {"resultid": 59, "roundid": 1, "heat": 20, "lane": 2, "racerid": 22, "finishtime": 4.605, "finishplace": 1},
    {"resultid": 60, "roundid": 1, "heat": 20, "lane": 3, "racerid": 30, "finishtime": 6.144, "finishplace": 3},
    {"resultid": 61, "roundid": 1, "heat": 21, "lane": 1, "racerid": 15, "finishtime": 6.41, "finishplace": 2},
    {"resultid": 62, "roundid": 1, "heat": 21, "lane": 2, "racerid": 12, "finishtime": 6.59, "finishplace": 3},
    {"resultid": 63, "roundid": 1, "heat": 21, "lane": 3, "racerid": 32, "finishtime": 4.835, "finishplace": 1},
    {"resultid": 64, "roundid": 1, "heat": 22, "lane": 1, "racerid": 20, "finishtime": 6.75, "finishplace": 2},
    {"resultid": 65, "roundid": 1, "heat": 22, "lane": 2, "racerid": 14, "finishtime": 6.434, "finishplace": 1},
    {"resultid": 66, "roundid": 1, "heat": 22, "lane": 3, "racerid": 13, "finishtime": 7.624, "finishplace": 3},
    {"resultid": 67, "roundid": 1, "heat": 23, "lane": 1, "racerid": 31, "finishtime": 6.11, "finishplace": 2},
    {"resultid": 68, "roundid": 1, "heat": 23, "lane": 2, "racerid": 16, "finishtime": 5.268, "finishplace": 1},
    {"resultid": 69, "roundid": 1, "heat": 23, "lane": 3, "racerid": 25, "finishtime": 6.355, "finishplace": 3},
    {"resultid": 70, "roundid": 1, "heat": 24, "lane": 1, "racerid": 21, "finishtime": 7.138, "finishplace": 2},
    {"resultid": 71, "roundid": 1, "heat": 24, "lane": 2, "racerid": 9, "finishtime": 7.808, "finishplace": 3},
    {"resultid": 72, "roundid": 1, "heat": 24, "lane": 3, "racerid": 34, "finishtime": 6.2, "finishplace": 1},
    {"resultid": 73, "roundid": 1, "heat": 25, "lane": 1, "racerid": 5, "finishtime": 7.637, "finishplace": 2},
    {"resultid": 74, "roundid": 1, "heat": 25, "lane": 2, "racerid": 8, "finishtime": 7.727, "finishplace": 3},
    {"resultid": 75, "roundid": 1, "heat": 25, "lane": 3, "racerid": 26, "finishtime": 6.244, "finishplace": 1},
    {"resultid": 76, "roundid": 1, "heat": 26, "lane": 1, "racerid": 33, "finishtime": 7.711, "finishplace": 3},
    {"resultid": 77, "roundid": 1, "heat": 26, "lane": 2, "racerid": 13, "finishtime": 6.156, "finishplace": 1},
    {"resultid": 78, "roundid": 1, "heat": 26, "lane": 3, "racerid": 19, "finishtime": 7.045, "finishplace": 2},
    {"resultid": 79, "roundid": 1, "heat": 27, "lane": 1, "racerid": 22, "finishtime": 5.775, "finishplace": 3},
    {"resultid": 80, "roundid": 1, "heat": 27, "lane": 2, "racerid": 25, "finishtime": 5.218, "finishplace": 2},
    {"resultid": 81, "roundid": 1, "heat": 27, "lane": 3, "racerid": 27, "finishtime": 4.786, "finishplace": 1},
    {"resultid": 82, "roundid": 1, "heat": 28, "lane": 1, "racerid": 24, "finishtime": 5.515, "finishplace": 2},
    {"resultid": 83, "roundid": 1, "heat": 28, "lane": 2, "racerid": 30, "finishtime": 4.518, "finishplace": 1},
    {"resultid": 84, "roundid": 1, "heat": 28, "lane": 3, "racerid": 12, "finishtime": 5.872, "finishplace": 3},
    {"resultid": 85, "roundid": 1, "heat": 29, "lane": 1, "racerid": 32, "finishtime": 6.429, "finishplace": 1},
    {"resultid": 86, "roundid": 1, "heat": 29, "lane": 2, "racerid": 4, "finishtime": 8.277, "finishplace": 3},
    {"resultid": 87, "roundid": 1, "heat": 29, "lane": 3, "racerid": 10, "finishtime": 7.075, "finishplace": 2},
    {"resultid": 88, "roundid": 1, "heat": 30, "lane": 1, "racerid": 9, "finishtime": 6.004, "finishplace": 1},
    {"resultid": 89, "roundid": 1, "heat": 30, "lane": 2, "racerid": 11, "finishtime": 6.61, "finishplace": 2},
    {"resultid": 90, "roundid": 1, "heat": 30, "lane": 3, "racerid": 29, "finishtime": 7.401, "finishplace": 3},
    {"resultid": 91, "roundid": 1, "heat": 31, "lane": 1, "racerid": 1, "finishtime": 4.663, "finishplace": 1},
    {"resultid": 92, "roundid": 1, "heat": 31, "lane": 2, "racerid": 2, "finishtime": 5.879, "finishplace": 3},
    {"resultid": 93, "roundid": 1, "heat": 31, "lane": 3, "racerid": 20, "finishtime": 5.644, "finishplace": 2},
    {"resultid": 94, "roundid": 1, "heat": 32, "lane": 1, "racerid": 18, "finishtime": 7.416, "finishplace": 3},
    {"resultid": 95, "roundid": 1, "heat": 32, "lane": 2, "racerid": 7, "finishtime": 5.554, "finishplace": 1},
    {"resultid": 96, "roundid": 1, "heat": 32, "lane": 3, "racerid": 16, "finishtime": 6.458, "finishplace": 2},
    {"resultid": 97, "roundid": 1, "heat": 33, "lane": 1, "racerid": 28, "finishtime": 6.179, "finishplace": 2},
    {"resultid": 98, "roundid": 1, "heat": 33, "lane": 2, "racerid": 19, "finishtime": 5.225, "finishplace": 1},
    {"resultid": 99, "roundid": 1, "heat": 33, "lane": 3, "racerid": 6, "finishtime": 7.157, "finishplace": 3},
    {"resultid": 100, "roundid": 1, "heat": 34, "lane": 1, "racerid": 17, "finishtime": 5.46, "finishplace": 1},
    {"resultid": 101, "roundid": 1, "heat": 34, "lane": 2, "racerid": 3, "finishtime": 6.516, "finishplace": 3},
    {"resultid": 102, "roundid": 1, "heat": 34, "lane": 3, "racerid": 8, "finishtime": 6.093, "finishplace": 2},
]

# Default RaceInfo settings for different test scenarios
RACEINFO_EMPTY = {
    "lane_count": "3",
}

RACEINFO_PRE_RACE = {
    "lane_count": "3",
    "NowRacingState": "0",
}

RACEINFO_MID_RACE = {
    "RoundID": "1",
    "Heat": "1",
    "ClassID": "1",
    "NowRacingState": "1",
    "lane_count": "3",
}

RACEINFO_COMPLETED = {
    "RoundID": "1",
    "Heat": "34",
    "ClassID": "1",
    "NowRacingState": "0",
    "lane_count": "3",
}


# Helper functions for fixture use
def get_racers_by_class(classid: int) -> list:
    """Get all racers for a specific class."""
    return [r for r in RACERS if r["classid"] == classid]


def get_race_results_by_round(roundid: int) -> list:
    """Get all race results for a specific round."""
    return [r for r in RACE_RESULTS if r["roundid"] == roundid]


def get_scheduled_heats(roundid: int = 1, num_heats: int = 5) -> list:
    """
    Generate scheduled heats without results (for pre-race testing).

    Returns RaceChart entries with finishtime=None and finishplace=None.
    """
    scheduled = []
    result_id = 1
    for heat in range(1, num_heats + 1):
        for lane in range(1, 4):  # 3 lanes
            # Pick a racer from the results to maintain consistency
            matching = [r for r in RACE_RESULTS
                       if r["roundid"] == roundid and r["heat"] == heat and r["lane"] == lane]
            if matching:
                racerid = matching[0]["racerid"]
            else:
                racerid = ((heat - 1) * 3 + lane)  # fallback
            scheduled.append({
                "resultid": result_id,
                "roundid": roundid,
                "heat": heat,
                "lane": lane,
                "racerid": racerid,
                "finishtime": None,
                "finishplace": None,
            })
            result_id += 1
    return scheduled
