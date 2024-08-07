# -*- coding: utf-8 -*-
"""wser-predictor-2.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tDWVc2K6XpJmqDqZWa9QL9fh3nqvyNiI
"""

# Import packages
import warnings, logging, os
logging.disable(logging.WARNING)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.simplefilter(action='ignore', category=FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tensorflow import feature_column as fc
import tensorflow as tf

# Function to format times
def getHours(strTime):
    if " " in strTime:
      strTime= strTime[0:str.find(strTime," ")]
    if strTime == "nan" or "-" in strTime:
        return 30.0
    else:
        strTime = str.split(strTime,':')
        return float(strTime[0]) + float(strTime[1])/60.0 + float(strTime[2])/3600.0

# Function to create input function to convert data to a tf.data.Dataset object
def make_input_fn(data_df, label_df, num_epochs=100, shuffle=True, batch_size=32):
    def input_function():
        ds = tf.data.Dataset.from_tensor_slices((dict(data_df),label_df))
        if shuffle:
            ds = ds.shuffle(1000)   # randomize order of data
        ds = ds.batch(batch_size).repeat(num_epochs)    # split into batches
        return ds
    return input_function

# Get user input for what type of model we want to run
print("---- SELECT MODEL TYPE ----")
print("(1) Silicon Valley Nerd: needs lots of splits, but is a bit more accurate.")
print("(2) Quick-And-Dirty: needs only 3 splits, but may be less accurate.")
modelType = int(input("Model Type: "))


print("---- SELECT CUTOFF ----")
print("Bronze Buckle/Beat Cutoff: 30.0")
print("Silver Buckle/Beat Sunrise: 24.0")
print("M1 Cougar/Beat Jim: 14.15")
print("F1 Cougar/Beat Courtney: 15.48")
cutoff = float(input("Finish Time (Hours): "))

# Temperature data
temps = {
    2024: [94, 63],
    2023: [80, 51],
    2022: [97, 70],
    2021: [101, 73],
    2020: [93, 66],
    2019: [83, 57],
    2018: [98, 61],
    2017: [95, 75],
    2016: [93, 60],
    2015: [91, 73],
    2014: [89, 59],
    2013: [102, 73],
    2012: [71, 51],
    2011: [82, 60],
    2010: [91, 66]
}

# Splits, features, labels
if modelType == 1:    # detailed model
  aidStationNames = ['Lyon Ridge', 'Red Star Ridge', 'Duncan Canyon', 'Robinson Flat', "Miller's Defeat", 'Dusty Corners', "Last Chance", "Devil's Thumb", "El Dorado Creek", "Michigan Bluff", "Foresthill"]
else:                 # simplified model
  aidStationNames = ['Robinson Flat', "Devil's Thumb", "Michigan Bluff"]

CATEGORICAL_COLUMNS = ['Gender']
NUMERIC_COLUMNS = np.concatenate([['Age', 'MinTemp', 'MaxTemp'], aidStationNames])
features = np.concatenate([CATEGORICAL_COLUMNS, NUMERIC_COLUMNS])
labels=['Time']

# Load data
startTrain = 2016
endTrain = 2023
testYear = 2022

df_individual = []
for year in range(startTrain,endTrain+1):
  if year != testYear and year != 2020:
    df = pd.read_csv(f'wser{year}.csv')
    df['MaxTemp'] = temps[year][0]
    df['MinTemp'] = temps[year][1]
    df_individual.append(df)
df_train = pd.concat(df_individual)

df_test = pd.read_csv(f'wser{testYear}.csv')
df_test['MaxTemp'] = temps[year][0]
df_test['MinTemp'] = temps[year][1]

# Format times
relevantSplits = np.concatenate([aidStationNames, labels])
for i in range(0, len(relevantSplits)):
    df_train[relevantSplits[i]] = df_train[relevantSplits[i]].apply(lambda x: getHours(str(x)))
    df_test[relevantSplits[i]] = df_test[relevantSplits[i]].apply(lambda x: getHours(str(x)))

# Split into features and labels for training and testing data
input_train = df_train[features].copy()
input_test = df_test[features].copy()
output_train = (df_train[labels].copy() < cutoff).astype(int)
output_test = (df_test[labels].copy() < cutoff).astype(int)

# Split into feature columns
feature_columns = []

for feature_name in CATEGORICAL_COLUMNS:
    vocabulary = input_train[feature_name].unique()
    feature_columns.append(tf.feature_column.categorical_column_with_vocabulary_list(feature_name,vocabulary))

for feature_name in NUMERIC_COLUMNS:
    feature_columns.append(tf.feature_column.numeric_column(feature_name, dtype=tf.float32))

# Create input data
input_train_fn = make_input_fn(input_train, output_train)
input_test_fn = make_input_fn(input_test, output_test, num_epochs=1, shuffle=False)

# Create linear classifier object which creates a model for us
linear_est = tf.estimator.LinearClassifier(feature_columns=feature_columns)

# Train the model!
print("Training Model...")
linear_est.train(input_train_fn)

# Evaluate the model!
result = linear_est.evaluate(input_test_fn)

# Report results
print("---- MODEL DETAILS ----")
s = ", "
print(f"Splits: {s.join(aidStationNames)}")
print(f"Training Set Size: {len(input_train)}")
print(f"Target Cutoff: {cutoff} hrs")
print(f"Accuracy: {result['accuracy']}")

# Generate confusion matrix
from sklearn import metrics
result = list(linear_est.predict(input_test_fn))
actual = []
predicted = []
for i in range(0, len(result)):
  finisher = result[i]
  predicted.append(int(round(finisher['probabilities'][1])))
  actual.append(int(df_test['Time'][i] < cutoff))
confusion_matrix = metrics.confusion_matrix(actual,predicted, normalize='true')
cm_display = metrics.ConfusionMatrixDisplay(confusion_matrix = confusion_matrix,
                                            display_labels=[f'Over {cutoff}', f'Sub-{cutoff}'])
cm_display.plot()
plt.title(f'WSER Sub-{cutoff} Hour Predictor\nConfusion Matrix')
plt.show()

# Let user make a prediction
print("---- PREDICT FINISH ----")

input_dict = {}
input_dict['Gender'] = input("Gender Category (M/F): ")
input_dict['Age'] = int(input("Age: "))
input_dict['MinTemp'] = float(input("Low Temperature (F): "))
input_dict['MaxTemp'] = float(input("High Temperature (F): "))

for aid in range(0, len(aidStationNames)):
  input_dict[aidStationNames[aid]] = getHours(input(f"Split at {aidStationNames[aid]} (hh:mm:ss):"))

df_test_input = pd.DataFrame([input_dict])

input_user_fn = make_input_fn(df_test_input, output_test.loc[0,:].copy(), num_epochs=1, shuffle=False)

result = list(linear_est.predict(input_user_fn))

finisher = result[0]
print(f"Probability of Sub-{cutoff} Finish: {finisher['probabilities'][1]}")