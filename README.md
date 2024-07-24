Tools in this repository:

- **Visualizations**: uses Python/SQL to create plots of finisher distributions as well as splits for individual finishers. The included file contains splits from 2023, but can be run with any historical data of the same format (available on the WSER website).
- **Buckle Predictor**: uses Python/TensorFlow to predict whether finishers will finish before a certain cutoff time. The model is trained on data from 2016-2023, including aid station splits, weather, and finisher age/gender category. To predict whether a finisher will beat a certain time, run wser-finish-predictor.py and input user data. Note that the aid station list can be modified depending which splits are available; however, using more splits (especially those later in the race) will yield more accurate results.
