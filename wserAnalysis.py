### IMPORTS
import mysql.connector
from mysql.connector import Error
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from wserSetup import *
from IPython.display import display

### SETUP
# Check that database exists
connection = createServerConnection(hostName, userName, password)
dbExists = len(readQuery(connection, "SHOW DATABASES LIKE '{}'".format(databaseName)))
if dbExists == 0:
    print("Database does not exist. Setting up...")
    createAndPopulateDatabase()
else:
    print("Database already exists!")

# Connect to database
print("Connecting to database")
connection = createDatabaseConnection(hostName, userName, password, databaseName)

### "HELPER" FUNCTIONS

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
        print("{} Hours".format(binLabels[i]))
        print("M: {}        F: {}".format(maleBins[i], femaleBins[i]))

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

# Looks at overall pacing distribution for a participant
def pacingIndividualParticipant(bibNumber, plotOutput=False):

    # Pre-allocate arrays
    mileMarkers = []    # mile markers
    overallTime = []    # elapsed time (hours) for the entire race at each mile marker
    elapsedPace = []    # average pace (minutes) for entire race at each mile marker
    splitPace   = []    # average pace (minutes) between mile markers

    splitQuery = lambda aidStationName, bibNumber: """
        SELECT hours, minutes, seconds
        FROM split_{}
        WHERE split_{}.bib LIKE '{}';""".format(aidStationName, aidStationName, bibNumber)

    # Get split at each aid station
    for i, aidStationName in enumerate(aidStations):

        # Query for split at aid station
        result = readQuery(connection, splitQuery(aidStationName, bibNumber))

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
        nameResults = readQuery(connection, "SELECT firstName, lastName FROM participants WHERE participants.bib LIKE '{}'".format(bibNumber))
        formattedName = "{} {}".format(nameResults[0][0], nameResults[0][1])
        plotPaceDistribution('WSER 2023 Pacing\n Bib #{}: {}'.format(bibNumber, formattedName), Elapsed=[mileMarkers,elapsedPace], Split=[mileMarkers, splitPace])

    # Return all data in case we want to use it
    return mileMarkers, elapsedPace, splitPace

# Looks at overall pacing distribution for entire field
def pacingEntireField(gender='%', plotOutput=False):
    
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

# Returns a subset of field as dataframe
# args: SQL "WHERE" clauses (i.e. ..."gender LIKE 'F'" or "hours < 24")
def finishersDataframe(*args):
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

### MAIN SCRIPT

# User interface
print("Western States 100 Pacing Analysis Tool")
print("***********************")
print("(1) Lookup a Single Participant")
print("(2) Lookup Entire Field")
print("(3) Compare Participant to Field")
print("(4) Plot Distribution of Finish Times")
print("(5) Lookup a Subset of Field")

cmd1 = str.strip(input(" > "))

# Operational modes
match cmd1:

    # Lookup a single participant
    case "1":
        bib = str.strip(input("Enter bib number > "))
        pacingIndividualParticipant(bib, plotOutput=True)

    # Lookup entire field
    case "2":
        gender = str.strip(input("Enter gender M or F, or ENTER for entire field > "))
        if gender == 'M' or gender == 'F':
            pacingEntireField(gender=gender, plotOutput=True)
        else:
            pacingEntireField(plotOutput=True)
    
    # Compare participant to field
    case "3":
        bib = str.strip(input("Enter bib number > "))
        gender = str.strip(input("Enter gender M or F, or ENTER for entire field > "))
        idvMiles, idvElapsed, idvSplit = pacingIndividualParticipant(bib)
        plotTitle = 'Compare Bib {} to Entire {} Field'.format(bib, gender)

        if (gender != 'M' and gender != 'F'):
            gender='%'
        oaMiles, oaElapsed, oaSplit = pacingEntireField(gender=gender)

        plotPaceDistribution(plotTitle, IndividualElapsedPace=[idvMiles, idvElapsed],
                                        IndividualSplitPace=[idvMiles, idvSplit],
                                        OverallElapsedPace=[oaMiles, oaElapsed],
                                        overallSplitpace=[oaMiles, oaSplit])
    
    # Plot finish time distribution
    case "4":
       finishTimeDistributionByBins()

    # Get statistical summary of a subset of field
    case "5":
        args = input("Enter SQL WHERE clauses for search parameters > ")
        df = finishersDataframe(args)
        display(df)
        display(df.describe())

    case _:
        print("Not a valid input.")
    

### CLEANUP
connection.close()