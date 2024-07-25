<h2>Western States Endurance Run Analysis</h2>
So you spent a little too much time listening to Freetrail, and now your life goal is to run 100.2 miles through blistering heat and technical terrain, all to collapse on a high school track while someone hands you a belt-buckle. Congratulations! Me too! And now I'm using my engineering degree to obsess over this race.

<h4>Tools in this repository:</h4>

- **Visualizations**: uses Python/SQL to create plots of finisher distributions as well as splits for individual finishers. The included file contains splits from 2023, but can be run with any historical data of the same format (available on the WSER website).
- **Buckle Predictor**: uses Python/TensorFlow to predict whether finishers will finish before a certain cutoff time. The model is trained on data from 2016-2023, including aid station splits, weather, and finisher age/gender category. To predict whether a finisher will beat a certain time, run wser-finish-predictor.py and input user data. Note that the aid station list can be modified depending which splits are available; however, using more splits (especially those later in the race) will yield more accurate results.
