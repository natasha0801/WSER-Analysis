### IMPORTS
import mysql.connector
from mysql.connector import Error
import pandas as pd

### GLOBAL VARIABLES
hostName = 'localhost'
userName = 'root'
password = 'password123'
databaseName = 'WSER2023'   # name of overall database
aidStationDetails = {
    "LyonRidge": 10.3,
    "RedStarRidge": 15.8,
    "DuncanCanyon": 24.4,
    "RobinsonFlat": 30.3,
    "MillersDefeat": 34.4,
    "DustyCorners": 38,
    "LastChance": 43.3,
    "DevilsThumb": 47.8,
    "ElDoradoCreek": 52.9,
    "MichiganBluff": 55.7,
    "Foresthill": 62,
    "Peachstone": 70.7,
    "FordsBar": 73,
    "RuckyChucky": 78,
    "GreenGate": 79.8,
    "AuburnLakeTrails": 85.2,
    "QuarryRd": 90.7,
    "PointedRocks": 94.3,
    "RobiePoint": 98.9,
    "Finish": 100.2
}
aidStations = list(aidStationDetails.keys())

### FUNCTIONS
# Creates to MySQL server
def createServerConnection(hostName, userName, userPass):
    connection = None
    try: 
        connection = mysql.connector.connect(
            host=hostName,
            user=userName,
            passwd=userPass
        )
        print("MySQL Server connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection

# Creates a database
def createDatabase(connection, databaseName):
    cursor = connection.cursor()
    try:
        cursor.execute("CREATE DATABASE " + databaseName)
        print("Database created successfully")
    except Error as err:
        print(f"Error: '{err}'")
    cursor.close()

# Connects to MySQL server (specific database)
def createDatabaseConnection(hostName, userName, userPass, db):
    connection = None
    try: 
        connection = mysql.connector.connect(
            host=hostName,
            user=userName,
            passwd=userPass,
            database=db
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection

# Executes a query
def executeQuery(connection, query):
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(query)
        connection.commit()
    except Error as err:
        print(f"Error: '{err}'")
    cursor.close()

# Reads a query
def readQuery(connection, query):
    cursor = connection.cursor(buffered=True)
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Error as err:
        print(f"Error: '{err}'")
    cursor.close()

# Splits a time (as a string) into hh, mm, ss integers
def formatTime(timeStr):
    try:
        if "/" in timeStr:          # string contains a date which must be removed
            timeStr = timeStr[timeStr.index(" ") + 1:]
        if " " in timeStr:
            timeStr = timeStr[:timeStr.index(" ")]
        return timeStr.split(":")
    except:
        print(timeStr)

# Creates & populates database
def createAndPopulateDatabase():
    print("Creating and populating database...")

    # Create database
    connection = createServerConnection(hostName, userName, password)      # connect to mySQL server
    executeQuery(connection, "DROP DATABASE IF EXISTS " + databaseName)     # housekeeping/debugging: clear database if it already exists
    createDatabase(connection, databaseName)                                # create a new database/clean slate
    
    connection = createDatabaseConnection(hostName, userName, password, databaseName)  # connect to new database

    # Create tables
    createParticipantTable = """
    CREATE TABLE participants (
        overallplace INT,
        bib VARCHAR(4) PRIMARY KEY,
        firstName VARCHAR(40),
        lastName VARCHAR(40),
        gender VARCHAR(2),
        age INT,
        city VARCHAR(40),
        state VARCHAR(40),
        country VARCHAR(40)
    );
    """
    createSplitTable = lambda splitName: """
    CREATE TABLE split_{}_{} (
        place INT NOT NULL,
        bib VARCHAR(4) PRIMARY KEY,
        location VARCHAR(40),
        hours INT,
        minutes INT,
        seconds INT
    );
    """.format(splitName)
    executeQuery(connection, createParticipantTable) 
    for station in aidStations:
        executeQuery(connection, createSplitTable(station))

    # Queries to populate tables
    insertIntoParticipants = lambda data: """
    INSERT INTO participants (overallplace, bib, firstName, lastName, gender, age, city, state, country)
    VALUES ({})""".format(data)

    insertIntoSplits = lambda splitName, data: """
    INSERT INTO split_{} (place, bib, location, hours, minutes, seconds)
    VALUES ({})""".format(splitName, data)

    # Populate tables from CSV
    wser2023 = pd.read_csv('wser2023.csv')                                  # Read WSER data
    for i, row in wser2023.iterrows():

        # Populate participant data
        participantData = ",".join([str(row['OverallPlace']), 
                                    '"' + str(row['Bib']) + '"', 
                                    '"' + str(row['FirstName']) + '"',
                                    '"' + str(row['LastName']) + '"',
                                    '"' + str(row['Gender']) + '"',
                                    str(row['Age']), 
                                    '"' + str(row['City']) + '"',
                                    '"' + str(row['State']) + '"',
                                    '"' + str(row['Country']) + '"'])
        executeQuery(connection, insertIntoParticipants(participantData))

        # Populate splits
        for station in aidStations:
            if '--:--' not in str(row[station]):                # make sure split data is available from that aid station
                [hh, mm, ss] = formatTime(str(row[station]))
                splitdata = ",".join([str(row[station + "Position"]),
                                    '"' + str(row['Bib']) + '"',
                                    '"' + station + '"',
                                    str(hh),
                                    str(mm),
                                    str(ss)])
                executeQuery(connection, insertIntoSplits(station, splitdata))
    ### CLEANUP
    connection.close()