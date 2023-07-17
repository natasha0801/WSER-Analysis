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
# kwargs should be 2D arrays of [label, milemarkers, paces]
def plotPaceDistribution(title, **kwargs):

    linestyles = ['-', '--']
    colors = plt.cm.rainbow(np.linspace(0, 1, 10))
    colorCounter = 0
    linestyleCounter = 1

    for key, values in kwargs.items():
        plt.plot(values[1], values[2], label=values[0], linestyle=linestyles[linestyleCounter],
                 color=colors[colorCounter], linewidth=0.8)
        linestyleCounter = 1 - linestyleCounter
        colorCounter = (colorCounter + (7*linestyleCounter)) % 10

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

    # Get some participant info
    try:
        firstName, lastName, bibNumber = nameAndBibNumber(searchTerm)
    except TypeError:
        return None     # participant is not found

    splitQuery = lambda aidStationName: """
        SELECT hours, minutes, seconds
        FROM split_{}
        WHERE split_{}.bib LIKE '{}';""".format(aidStationName, aidStationName, bibNumber)

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
    if plotOutput:
        plotPaceDistribution('WSER 2023 Pacing\n Bib #{}: {} {}'.format(bibNumber, firstName, lastName),
                             Elapsed=['Elapsed', mileMarkers,elapsedPace],
                             Split=['Split', mileMarkers, splitPace])

    connection.close()

    # Return all data in case we want to use it
    return mileMarkers, elapsedPace, splitPace

# Returns a subset of field as dataframe and plots pacing
# searchParams: SQL "WHERE" clauses (i.e. ..."gender LIKE 'F'" or "hours < 24")
def subsetOfField(searchParams, plotOutput=False):

    print("Connecting to database")
    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    # Format queries
    if len(searchParams) > 0 and "WHERE" not in searchParams:
        searchParams = "WHERE " + searchParams

    finishersQuery = """
        SELECT participants.bib, firstName, lastName, age, gender, place, hours, minutes, seconds
        FROM participants
        JOIN split_finish
            ON participants.bib LIKE split_finish.bib {}
        """.format(searchParams)
    splitQuery = lambda aidStationName, bibNumber: """
        SELECT hours, minutes, seconds
        FROM split_{}
        WHERE split_{}.bib LIKE '{}'""".format(aidStationName, aidStationName, bibNumber)

    # set up arrays
    mileMarkers = list(aidStationDetails.values())          # mile markers of each aid station
    averageOverallPace = np.zeros(len(mileMarkers))         # average overall pace of participants at each aid station
    averageSplitPace = np.zeros(len(mileMarkers))           # average split pace of participants at each aid station
    numDatapointsOverall = np.zeros(len(mileMarkers))       # number of datapoints (to calculate avg)
    numDatapointsSplit = np.zeros(len(mileMarkers))         # number of datapoints (to calculate avg)

    # get all finishers
    finishers = readQuery(connection, finishersQuery)
    finishersList = []

    # iterate through participants
    for finisher in finishers:
        finishersList.append(list(finisher))
        bib = finisher[0]

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

    # use total times and number of datapoints to calculate avg pace for entire field
    averageOverallPace = np.divide(averageOverallPace, numDatapointsOverall)
    averageSplitPace = np.divide(averageSplitPace, numDatapointsSplit)

    # Plot results
    if (plotOutput):
        title = 'WSER 2023 Pacing \n Field Subset: {}'.format(searchParams)
        plotPaceDistribution(title, Elapsed=['Elapsed', mileMarkers,averageOverallPace],
                             Split=['Split', mileMarkers,averageSplitPace])
    columns = ['bib', 'firstName', 'lastName', 'age', 'gender', 'place', 'hours', 'minutes', 'seconds']
    return pd.DataFrame(finishersList, columns=columns), mileMarkers, averageOverallPace, averageSplitPace

# Distribution of finish times by age
def distributionByAge(numBins=10):

    print("Connecting to database")
    connection = createDatabaseConnection(hostName, userName, password, databaseName)

    # Set up bins
    minAge = readQuery(connection, "SELECT MIN(age) FROM participants")[0][0]
    maxAge = readQuery(connection, "SELECT MAX(age) FROM participants")[0][0]
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

# Gets participant name and bib number from either bib, first name, or last name
def nameAndBibNumber(searchTerm):

    connection = createDatabaseConnection(hostName, userName, password, databaseName)
    infoQuery = ""

    # User entered a bib number if search term contains numeric digits 0 - 9; otherwise lookup by name
    if not (" " in searchTerm) and not searchTerm.isalpha():
        infoQuery = """
            SELECT firstName, lastName, bib
            FROM participants
            WHERE participants.bib LIKE '{}'""".format(searchTerm)
    else:
        firstAndLast = searchTerm.split(" ")
        if len(firstAndLast) == 2:
            infoQuery = """
            SELECT firstName, lastName, bib
            FROM participants
            WHERE participants.lastName LIKE '{}' 
            AND participants.firstName LIKE '{}'""".format(str(firstAndLast[1]), str(firstAndLast[0]))
        else:
            infoQuery = """
            SELECT firstName, lastName, bib
            FROM participants
            WHERE participants.lastName LIKE '{}' 
            OR participants.firstName LIKE '{}'""".format(str(firstAndLast[0]), str(firstAndLast[0]))

    # Get participant basic info
    basicInfo = readQuery(connection, infoQuery)
    connection.close()
    if (len(basicInfo) != 0):
        firstName = basicInfo[0][0]
        lastName = basicInfo[0][1]
        bibNumber = basicInfo[0][2]
        return firstName, lastName, bibNumber
    else:
        return None     # participant not found

### MAIN SCRIPT
def main():

    # Check that database exists
    databaseSetup()

    # Set up global params
    endProgram = False

    # User interface
    print("Western States 100 Pacing Analysis Tool")
    print("***********************")

    # Main loop
    while not endProgram:
        print("MAIN MENU")
        print("***********************")
        print("(1) Lookup a Single Participant")
        print("(2) Compare Participant to Field")
        print("(3) Compare Two Participants")
        print("(4) Plot Distribution of Finish Times")
        print("(5) Lookup a Subset of Field")
        print("(6) Finish Times By Age")
        print("(7) Exit")
        cmd = str.strip(input(" > "))

        # Operational modes
        match cmd:

            # Lookup a single participant
            case "1":
                searchTerm = str.strip(input("Enter first name, last name, or bib number > "))
                try:
                    miles, elapsed, splits = pacingIndividualParticipant(searchTerm, plotOutput=True)
                except TypeError:
                    print("Participant not found using search terms: {}".format(searchTerm))

            # Compare participant to field
            case "2":
                idvSearch = str.strip(input("Enter first name, last name, or bib number > "))
                fieldSearch = str.strip(input("Enter SQL WHERE clause for entire field params, or ENTER for entire field > "))
                try:
                    try:
                        idvMiles, idvElapsed, idvSplit = pacingIndividualParticipant(idvSearch)
                        idvFirst, idvLast, idvBib = nameAndBibNumber(idvSearch)
                    except TypeError:
                        print("Cannot find participant by search terms: {}".format(idvSearch))
                        raise TypeError

                    title = 'Compare {} {} (Bib {}) to Field Subset \n {}'.format(idvFirst, idvLast, idvBib, fieldSearch)

                    df, oaMiles, oaElapsed, oaSplit = subsetOfField(fieldSearch)

                    plotPaceDistribution(title, IndividualElapsedPace=['{} Elapsed'.format(idvLast), idvMiles, idvElapsed],
                                                IndividualSplitPace=['{} Split'.format(idvLast), idvMiles, idvSplit],
                                                OverallElapsedPace=['Field Average Elapsed', oaMiles, oaElapsed],
                                                OverallSplitPace=['Field Average Split', oaMiles, oaSplit])
                except TypeError:
                    pass

            # Compare participants
            case "3":
                search1 = str.strip(input("Enter first name or bib number > "))
                search2 = str.strip(input("Enter second name or bib number > "))
                try:
                    try:
                        mi1, elapsed1, split1 = pacingIndividualParticipant(search1)
                        first1, last1, bib1 = nameAndBibNumber(search1)
                    except TypeError:
                        print("Cannot find participant by search terms {}".format(search1))
                        raise TypeError
                    try:
                        mi2, elapsed2, split2 = pacingIndividualParticipant(search2)
                        first2, last2, bib2 = nameAndBibNumber(search2)
                    except TypeError:
                        print("Cannot find participant by search terms {}".format(search2))
                        raise TypeError
                    plotTitle = 'WSER Pacing: {} (Bib {}) and {} (Bib {})'.format(last1, bib1, last2, bib2)
                    plotPaceDistribution(plotTitle, ElapsedPace1=['{} Elapsed'.format(last1), mi1, elapsed1],
                                         SplitPace1=['{} Split'.format(last1), mi1, split1],
                                         ElapsedPace2=['{} Elapsed'.format(last2), mi2, elapsed2],
                                         SplitPace2=['{} Split'.format(last2), mi2, split2])
                except TypeError:
                    pass

            # Plot finish time distribution
            case "4":
                finishTimeDistributionByBins()

            # Get statistical summary of a subset of field
            case "5":
                args = str.strip(input("Enter SQL search parameters > "))   # user inputs end of "where" clause
                if "WHERE" in args:                           # but we design in case user types "WHERE" anyway
                    args = str.strip(args[5:])
                df, miles, elapsed, splits = subsetOfField(args, plotOutput=True)
                display(df)
                display(df.describe())

            # Finish time by age
            case "6":
                numBins = int(input("Enter number of age bins > "))
                distributionByAge(numBins)

            case "7":
                print("Exiting program.")
                endProgram = True
            case _:
                print("Not a valid input.")
                endProgram = True
        print("***********************")


if __name__ == "main":
    main()

main()      # debug only
