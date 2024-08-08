<h2>Western States Endurance Run Analysis</h2>
So you spent a little too much time listening to Freetrail, and now your life goal is to run 100.2 miles through blistering heat and technical terrain, all to collapse on a high school track while someone in a Hawaiian shirt hands you a belt-buckle and a stack of pancakes. Congratulations! Me too! 

For most of us, many years of training, lottery tickets, and sheer luck stand between us and actually running Western States. For some of us (me), we are going stir-crazy with injury before we can even start on those aforementioned steps. But for now, I'm living vicariously through previous WSER athletes, and using my two engineering degrees to model how fast someone can run from Olympic Valley to Placer High School.

<h4>Tools in this repository:</h4>

<ul>
      <li><b>Buckle Predictor</b>: uses Python/TensorFlow to predict finish time/category. The model is trained on data from 2016-2023, including aid station splits, weather, and finisher age/gender category.
      <ul>
            <li>To predict whether a finisher will beat a certain time, run wser-finish-predictor.py and input user data.</li>
            <li>To predict which buckle a runner will earn (if any), run wser-buckle-predictor.py and input user data.</li>
            <li>Note that the aid station list can be modified depending which splits are available; however, using more splits (especially those later in the race) will yield more accurate results.</li>
      </ul>
      </li>
      <li><b>Visualizations</b>: uses Python/SQL to create plots of finisher distributions as well as splits for individual finishers. The included file contains splits from 2023, but can be run with any historical data of the same format (available on the WSER website).</li>
</ul>
