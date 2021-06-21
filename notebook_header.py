# HEEDY NOTEBOOK HEADER
# This code is run automatically on kernel start by heedy
# It is assumed that jupyter is set up to inline images, and to import pylab

# You will need an app access token to connect to heedy
import os
import heedy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sb

%matplotlib inline

plt.style.use("seaborn")  # Use the seaborn style
plt.rcParams["figure.figsize"] = (11.0, 8.0)  # Make figures larger by default
plt.rcParams['figure.dpi'] = 80

# Set heedy timeseries to output pandas dataframes
heedy.Timeseries.output_type = "dataframe"

# Load the heedy environment
h = heedy.App(os.getenv("HEEDY_ACCESS_TOKEN"), os.getenv("HEEDY_SERVER_URL")).owner

# Read the user, so that print(h) gives cached info. This might fail if the app doesn't
# have permissions to read the owner.
try:
    h.read()
except:
    pass
