import numpy as np
import pandas as pd
from numpy.linalg import inv
from scipy.special import expit  # Sigmoid function

def dsp(data, W, mu):
    """
    Main function for sex estimation using the DSP2 method.
    
    Parameters:
    - data (pd.DataFrame): Input data with 10 columns (PUM, SPU, DCOX, etc.).
    - W (pd.DataFrame): Covariance matrix.
    - mu (pd.DataFrame): Means for 'F' (female) and 'M' (male).
    
    Returns:
    - dict: Results with 'Sex estimate', 'ProbF', and 'ProbM'.
    """
    # Initialize an empty results DataFrame
    res = {
        'Sex estimate' : 'I',
        'ProbF' : 0,
        'ProbM' : 0
    }
    
    for i, row in data.iterrows():
        # Remove NaNs
        x = row.dropna()
        variables = x.index.tolist()
        
        # Subset matrices
        x = x.values.reshape(-1, 1)  # Convert row to column vector
        w = W.loc[variables, variables].values
        muF = mu.loc['F', variables].values.reshape(-1, 1)
        muM = mu.loc['M', variables].values.reshape(-1, 1)
        
        # Calculate inverse of covariance matrix
        w_inv = inv(w)
        
        # Mahalanobis distances
        DF = (x - muF).T @ w_inv @ (x - muF)
        DM = (x - muM).T @ w_inv @ (x - muM)
        
        # Posterior probability for being a female
        pF = expit(0.5 * (DM - DF))  # Sigmoid function
        
        # Results
        res["ProbF"] = round(float(pF), 3)
        res["ProbM"] = round(1 - float(pF), 3)
        
        if pF >= 0.95:
            res["Sex estimate"] = "F"
        elif pF <= 0.05:
            res["Sex estimate"] = "M"
        else:
            res["Sex estimate"] = "I"
    
    return res