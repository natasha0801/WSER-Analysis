### IMPORTS
import mysql.connector
from mysql.connector import Error
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from wserSetup import *
from IPython.display import display

### "HELPER" FUNCTIONS

# Checks that database exists
def databaseSetup():
    connection = createServerConnection(hostName, userName, password)
    dbExists = len(readQuery(connection, "SHOW DATABASES LIKE '{}'".format(databaseName)))
    if dbExists == 0:
        print("Database does not exist. Setting up...")
        createAndPopulateDatabase()
    else:
        print("Database already exists!")
    connection.close()

# Converts hh, mm, ss to fractional hours
def fractionalHours(hh, mm, ss):
    return hh + (mm / 60.0) + (ss / 3600.0)

# Calculates pace in mm.frac
def calculatePace(miles, hours):
    return 60.0 * hours / miles

# Plot pacing over course of race
# Title --> title of plot
# kwargs should be 2D arrays of [milemarkers, paces]
def plotPaceDistribution(title, **kwargs):

    linestyles = ['-', '--']
    currentLinestyle = 0

    for label, markers in kwargs.items():
        plt.plot(markers[0], markers[1], label=label, linestyle=linestyles[currentLinestyle])
        currentLinestyle = (1 - currentLinestyle)
    plt.xlabel('Miles')
    plt.ylabel('Mile Pace (minutes)')
    plt.grid()
    plt.title(title)
    plt.legend()
    plt.show()

### ANALYSIS FUNCTIONS

# Sorts finishers by 2-hr bins
def finishTimeDistributionByBins():

    print("Connecting to database")
    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    # Query to get number of finish times within a bin
    binFinishQuery = lambda gender, lowerBin, upperBin: """
    SELECT COUNT(*)
    FROM participants
    JOIN split_finish
        ON split_finish.bib LIKE participants.bib
    WHERE participants.gender LIKE '{}'
    AND split_finish.hours >= {}
    AND split_finish.hours < {};""".format(gender, lowerBin, upperBin)

    bins = [0,16,18,20,22,24,26,28,30]      # finish time markers
    numBins = len(bins) - 1                   # number of bins
    maleBins = np.zeros(numBins)              # number of male finishers in each bin
    femaleBins = np.zeros(numBins)            # number of female finishers in each bin
    binLabels = [None] * numBins              # bin labels

    print("NUMBER OF FINISHERS IN HOURLY BINS")
    print("----------------------------------")

    for i in range(0, numBins):

        # upper and lower hourly limits of bin
        lowerBin = bins[i]                  
        upperBin = bins[i+1]

        # get number of finishers within that time bin
        maleBins[i] = readQuery(connection, binFinishQuery('M', lowerBin, upperBin))[0][0]
        femaleBins[i] = readQuery(connection, binFinishQuery('F', lowerBin, upperBin))[0][0]

        # display results
        binLabels[i] = "{}-{}".format(lowerBin, upperBin)

    # Plot results
    xAxis = np.arange(numBins)
    plt.bar(xAxis - 0.2, femaleBins, 0.4, label='F')
    plt.bar(xAxis + 0.2, maleBins, 0.4, label='M')
    plt.xticks(xAxis, binLabels)
    plt.xlabel('Finish Time (Hours)')
    plt.ylabel('Number of Finishers')
    plt.title('WSER 2023 Finish Time Distribution')
    plt.legend()
    plt.show()

    connection.close()

# Looks at overall pacing distribution for a participant
def pacingIndividualParticipant(searchTerm, plotOutput=False):

    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    # Pre-allocate arrays
    mileMarkers = []    # mile markers
    overallTime = []    # elapsed time (hours) for the entire race at each mile marker
    elapsedPace = []    # average pace (minutes) for entire race at each mile marker
    splitPace   = []    # average pace (minutes) between mile markers
    firstName = ""
    lastName = ""
    bibNumber = ""

    # User entered a bib number if search term contains numeric digits 0 - 9; otherwise lookup by name
    splitQuery = ""
    infoQuery = ""
    if searchTerm.isalpha() == False:
        splitQuery = lambda aidStationName: """
            SELECT hours, minutes, seconds
            FROM split_{}
            WHERE split_{}.bib LIKE '{}';""".format(aidStationName, aidStationName, searchTerm)
        infoQuery = """
            SELECT firstName, lastName, bib
            FROM participants
            WHERE participants.bib LIKE '{}'""".format(searchTerm)
    else:
        nameSearch = ""
        firstAndLast = searchTerm.split(" ")
        print(firstAndLast)
        if len(firstAndLast) == 2:
            nameSearch = "WHERE participants.lastName LIKE '{}' OR participants.firstName LIKE '{}'".format(str(firstAndLast[1]), str(firstAndLast[0]))
        else:
            nameSearch = "WHERE participants.lastName LIKE '{}' OR participants.firstName LIKE '{}'".format(str(firstAndLast[0]), str(firstAndLast[0]))

        splitQuery = lambda aidStationName: """
            SELECT hours, minutes, seconds
            FROM split_{}
            JOIN participants
                ON participants.bib = split_{}.bib
            {}""".format(aidStationName, aidStationName, nameSearch)
        infoQuery = """
            SELECT firstName, lastName, bib
            FROM participants
            {}""".format(nameSearch)

    # Get participant basic info
    basicInfo = readQuery(connection, infoQuery)
    if (len(basicInfo) != 0):
        firstName = basicInfo[0][0]
        lastName = basicInfo[0][1]
        bibNumber = basicInfo[0][2]
    else:
        print("Participant not found.")
        return

    # Get split at each aid station
    for i, aidStationName in enumerate(aidStations):

        # Query for split at aid station
        result = readQuery(connection, splitQuery(aidStationName))

        if(len(result) != 0):       # check that a split was saved at that aid station

            # Hours, minutes, second split at aid station
            hh = result[0][0]
            mm = result[0][1]
            ss = result[0][2]

            # Save data from that aid station
            mileMarkers.append(aidStationDetails[aidStationName])
            overallTime.append(fractionalHours(hh, mm, ss))
            elapsedPace.append(calculatePace(mileMarkers[-1], overallTime[-1]))
            if i == 0:
                splitPace.append(elapsedPace[-1])
            else:
                splitPace.append(calculatePace(mileMarkers[-1] - mileMarkers[-2], overallTime[-1] - overallTime[-2]))

    # Plot results
    if (plotOutput):
        plotPaceDistribution('WSER 2023 Pacing\n Bib #{}: {} {}'.format(bibNumber, firstName, lastName), Elapsed=[mileMarkers,elapsedPace], Split=[mileMarkers, splitPace])

    connection.close()

    # Return all data in case we want to use it
    return mileMarkers, elapsedPace, splitPace

# Looks at overall pacing distribution for entire field
def pacingEntireField(gender='%', plotOutput=False):


    print("Connecting to database")
    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    # set up arrays
    mileMarkers = list(aidStationDetails.values())          # mile markers of each aid station
    averageOverallPace = np.zeros(len(mileMarkers))         # average overall pace of participants at each aid station
    averageSplitPace = np.zeros(len(mileMarkers))           # average split pace of participants at each aid station
    numDatapointsOverall = np.zeros(len(mileMarkers))
    numDatapointsSplit = np.zeros(len(mileMarkers))

   # useful queries
    entireFieldQuery = """
        SELECT participants.bib
        FROM participants
        JOIN split_finish
            ON participants.bib LIKE split_finish.bib
        WHERE gender LIKE '{}'""".format(gender)
    splitQuery = lambda aidStationName, bibNumber: """
        SELECT hours, minutes, seconds
        FROM split_{}
        WHERE split_{}.bib LIKE '{}'""".format(aidStationName, aidStationName, bibNumber)
    
    # get all finishers
    allBibs = readQuery(connection, entireFieldQuery)

    # iterate through participants
    for b in list(allBibs):
        bib = b[0]

        # iterate through aid stations
        for i, aidStation in enumerate(aidStations):

            # get participant result at that aid station
            currentSplitData = readQuery(connection, splitQuery(aidStation, bib))

            # if participant has non-null results at an aid station, add that to overall pacing
            if len(currentSplitData) != 0:
                hh = currentSplitData[0][0]
                mm = currentSplitData[0][1]
                ss = currentSplitData[0][2]
                decimalTime = fractionalHours(hh, mm, ss)
                participantOverallPace = calculatePace(mileMarkers[i], decimalTime)
                averageOverallPace[i] = averageOverallPace[i] + participantOverallPace
                numDatapointsOverall[i] = numDatapointsOverall[i] + 1

                # if participant has non-null results at both current AND prev aid station, add that to split pacing
                # TODO: figure out how to make this more computationally efficient
                if i == 0:
                    averageSplitPace[i] = averageSplitPace[i] + participantOverallPace
                    numDatapointsSplit[i] = numDatapointsSplit[i] + 1
                else:
                    previousSplitData = readQuery(connection, splitQuery(aidStations[i-1], bib))
                    if len(previousSplitData) != 0:
                        hh_prev = previousSplitData[0][0]
                        mm_prev = previousSplitData[0][1]
                        ss_prev = previousSplitData[0][2]
                        decimalTimePrev = fractionalHours(hh_prev, mm_prev, ss_prev)
                        participantSplitPace = calculatePace((mileMarkers[i] - mileMarkers[i-1]), decimalTime - decimalTimePrev)
                        averageSplitPace[i] = averageSplitPace[i] + participantSplitPace
                        numDatapointsSplit[i] = numDatapointsSplit[i] + 1

            else:
                print("NOTE: Bib # {} has no results at {} (mile {}).".format(bib, aidStation, mileMarkers[i]))
    averageOverallPace = np.divide(averageOverallPace, numDatapointsOverall)
    averageSplitPace = np.divide(averageSplitPace, numDatapointsSplit)

    # Plot results
    if (plotOutput):
        if gender == '%':
            title = 'WSER 2023 Pacing\n Entire Field'
        else:
            title = 'WSER 2023 Pacing \n Entire {} Field'.format(gender)
        plotPaceDistribution(title, Elapsed=[mileMarkers,averageOverallPace], Split=[mileMarkers,averageSplitPace])

    return mileMarkers, averageOverallPace, averageSplitPace

# Returns a subset of field as dataframe
# args: SQL "WHERE" clauses (i.e. ..."gender LIKE 'F'" or "hours < 24")
def finishersDataframe(*args):

    print("Connecting to database")
    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    searchParamString = " AND ".join(args)
    finishersQuery = """
        SELECT firstName, lastName, age, gender, place, hours, minutes, seconds
        FROM split_finish
        JOIN participants
            ON participants.bib LIKE split_finish.bib
        WHERE {}
        """.format(searchParamString)
    
    finishers = readQuery(connection, finishersQuery)
    finishersList = []
    for finisher in finishers:
        finishersList.append(list(finisher)
                             )
    columns = ['firstName', 'lastName', 'age', 'gender', 'place', 'hours', 'minutes', 'seconds']
    return pd.DataFrame(finishersList, columns=columns)

# Distribution of finish times by age
def distributionByAge(numBins=10):

    print("Connecting to database")
    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    # Set up bins
    minAge = readQuery(connection, "SELECT MIN(age) FROM participants")[0][0]
    maxAge = readQuery(connection, "SELECT MAX(age) FROM participants")[0][0]
    print("min age: {}".format(minAge))
    print("max age: {}".format(maxAge))
    binSize = np.ceil((maxAge - minAge) / numBins)
    binLimits = np.arange(minAge - np.floor(binSize/2), maxAge + np.ceil(binSize/2), binSize, dtype=int)     # age group bins
    meanHrsM = np.zeros(numBins)                      # store average times (M finishers)
    meanHrsW = np.zeros(numBins)                      # store average times (W finishers)
    binLabels = [""] * numBins

    # Get participants in each bin
    queryByAgeAndGender = lambda min, max, gender: """
        SELECT AVG(hours), AVG(minutes), AVG(seconds), COUNT(*)
        FROM split_finish
        JOIN participants
            ON participants.bib LIKE split_finish.bib
        WHERE participants.age >= {} AND participants.age < {} AND participants.gender LIKE '{}';
    """.format(min, max, gender)

    for i in range(0, numBins):
        results_m = readQuery(connection, queryByAgeAndGender(binLimits[i], binLimits[i+1], 'M'))
        results_w = readQuery(connection, queryByAgeAndGender(binLimits[i], binLimits[i+1], 'F'))
        hm, mm, sm, cm = results_m[0][0], results_m[0][1], results_m[0][2], results_m[0][3]
        hw, mw, sw, cw = results_w[0][0], results_w[0][1], results_w[0][2], results_w[0][3]

        if float(cm) != 0:
            meanHrsM[i] = fractionalHours(float(hm), float(mm), float(sm))
        else:
            meanHrsM[i] = 0
        if float(cw) != 0:
            meanHrsW[i] = fractionalHours(float(hw), float(mw), float(sw))
        else:
            meanHrsW[i] = 0
        binLabels[i] = "{}-{}".format(binLimits[i], binLimits[i+1]-1)

    # Plot results
    xAxis = np.arange(numBins)
    plt.bar(xAxis - 0.2, meanHrsW, 0.4, label='F')
    plt.bar(xAxis + 0.2, meanHrsM, 0.4, label='M')
    plt.xticks(xAxis, binLabels)
    plt.xlabel('Age')
    plt.ylabel('Mean Finish Time')
    plt.title('WSER Finish Time By Age')
    plt.legend()
    plt.show()

### MAIN SCRIPT
def main():

    # Check that database exists
    databaseSetup()

    # Set up global params
    exit = False

    # User interface
    print("Western States 100 Pacing Analysis Tool")
    print("***********************")

    # Main loop
    while (exit == False):
        print("MAIN MENU")
        print("***********************")
        print("(1) Lookup a Single Participant")
        print("(2) Lookup Entire Field")
        print("(3) Compare Participant to Field")
        print("(4) Plot Distribution of Finish Times")
        print("(5) Lookup a Subset of Field")
        print("(6) Finish Times By Age")
        print("(7) Compare Two Participants")
        print("(8) Exit")
        cmd = str.strip(input(" > "))

        # Operational modes
        match cmd:

            # Lookup a single participant
            case "1":
                bib = str.strip(input("Enter first name, last name, or bib number > "))
                pacingIndividualParticipant(bib, plotOutput=True)

            # Lookup entire field
            case "2":
                gender = str.strip(input("Enter gender M or F, or ENTER for entire field > "))
                if ("M" not in gender and "F" not in gender):
                    gender = "%"
                pacingEntireField(gender=gender, plotOutput=True)

            # Compare participant to field
            case "3":
                bib = str.strip(input("Enter first name, last name, or bib number > "))
                gender = str.strip(input("Enter gender M or F, or ENTER for entire field > "))
                plotTitle = 'Compare Bib {} to Entire {} Field'.format(bib, gender)
                if ("M" not in gender and "F" not in gender):
                    gender = "%"
                idvMiles, idvElapsed, idvSplit = pacingIndividualParticipant(bib)
                oaMiles, oaElapsed, oaSplit = pacingEntireField(gender=gender)
                plotPaceDistribution(plotTitle, IndividualElapsedPace=[idvMiles, idvElapsed],
                                                IndividualSplitPace=[idvMiles, idvSplit],
                                                OverallElapsedPace=[oaMiles, oaElapsed],
                                                overallSplitPace=[oaMiles, oaSplit])

            # Plot finish time distribution
            case "4":
                finishTimeDistributionByBins()

            # Get statistical summary of a subset of field
            case "5":
                args = input("Enter SQL WHERE clauses for search parameters > ")
                df = finishersDataframe(args)
                display(df)
                display(df.describe())

            # Finish time by age
            case "6":
                numBins = int(input("Enter number of age bins > "))
                distributionByAge(numBins)

            # Compare participants
            case "7":
                bib1 = str.strip(input("Enter first name or bib number > "))
                bib2 = str.strip(input("Enter second name or bib number > "))
                mi1, elapsed1, split1 = pacingIndividualParticipant(bib1)
                mi2, elapsed2, split2 = pacingIndividualParticipant(bib2)
                plotTitle = 'WSER Pacing: (1) {} and (2) {}'.format(bib1, bib2)
                plotPaceDistribution(plotTitle, ElapsedPace1=[mi1, elapsed1],
                                     SplitPace1=[mi1, split1],
                                     ElapsedPace2=[mi2, elapsed2],
                                     SplitPace2=[mi2, split2])
            case "8":
                print("Exiting program.")
                exit = True
            case _:
                print("Not a valid input.")
                exit = True


if __name__ == "main":
    main()

main()
