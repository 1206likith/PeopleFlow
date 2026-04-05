import numpy as np
import scipy.stats as stats
import pandas as pd
from typing import List, Dict, Any

class ExperimentStatsEngine:
    """
    Computes statistical metrics (Confidence Intervals, T-Tests, Multi-run aggregations)
    for simulation experiments to ensure academic validity of results.
    """
    
    @staticmethod
    def compute_confidence_intervals(data: List[float], confidence: float = 0.95) -> Dict[str, float]:
        """Calculates the mean and the confidence interval bound for a dataset."""
        a = np.array(data)
        n = len(a)
        if n == 0:
            return {"mean": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "std": 0.0}
        
        m, se = np.mean(a), stats.sem(a)
        if n < 2 or se == 0:
            return {"mean": float(m), "ci_lower": float(m), "ci_upper": float(m), "std": 0.0}
            
        h = se * stats.t.ppf((1 + confidence) / 2., n-1)
        return {
            "mean": float(m),
            "ci_lower": float(m - h),
            "ci_upper": float(m + h),
            "std": float(np.std(a))
        }

    @staticmethod
    def compute_statistical_significance(data_a: List[float], data_b: List[float]) -> Dict[str, Any]:
        """Performs a strict two-sided T-test (Welch's) to compare two different simulation policies."""
        if len(data_a) < 2 or len(data_b) < 2:
            return {"p_value": 1.0, "significant": False, "t_statistic": 0.0}

        array_a = np.array(data_a, dtype=float)
        array_b = np.array(data_b, dtype=float)
        if np.allclose(array_a, array_b) or (np.std(array_a) == 0.0 and np.std(array_b) == 0.0):
            return {"p_value": 1.0, "significant": False, "t_statistic": 0.0}

        t_stat, p_val = stats.ttest_ind(array_a, array_b, equal_var=False)
        return {
            "p_value": float(p_val),
            "significant": bool(p_val < 0.05),
            "t_statistic": float(t_stat)
        }

    @staticmethod
    def aggregate_time_series(runs_data: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Averages time-series data (like evacuation curve) across multiple runs.
        Requires identical time steps, or relies on Pandas grouping by 'step'.
        """
        if not runs_data:
            return pd.DataFrame()
            
        # Combine all runs into one df
        combined = pd.concat(runs_data, keys=range(len(runs_data)), names=['run_id'])
        # Group by the individual simulation step (or time column if provided)
        aggregated = combined.groupby('step').agg({
            'evacuated': ['mean', 'std'],
            'remaining': ['mean', 'std'],
            'mean_speed': ['mean', 'std']
        })
        
        # Flatten multi-level columns
        aggregated.columns = ['_'.join(col).strip() for col in aggregated.columns.values]
        return aggregated.reset_index()
