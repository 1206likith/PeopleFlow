import matplotlib.pyplot as plt
import plotly.graph_objects as go
import numpy as np
import os
from typing import List

class MetricVisualizer:
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
    
    @classmethod
    def setup(cls):
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        
    @classmethod
    def plot_evacuation_curve(cls, time_data: List[float], mean_remaining: List[float], std_remaining: List[float] = None, filename: str = "evac_curve.png") -> str:
        cls.setup()
        plt.figure(figsize=(10, 6))
        
        plt.plot(time_data, mean_remaining, linewidth=2, color='#1f77b4', label='Remaining Agents (Mean)')
        
        if std_remaining is not None and len(std_remaining) == len(time_data):
            upper_bound = np.array(mean_remaining) + np.array(std_remaining)
            lower_bound = np.maximum(0, np.array(mean_remaining) - np.array(std_remaining))
            plt.fill_between(time_data, lower_bound, upper_bound, color='#1f77b4', alpha=0.2, label='±1 Std Dev')

        plt.title('Evacuation Curve', fontsize=14)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Agents Remaining', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        
        path = os.path.join(cls.OUTPUT_DIR, filename)
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    @classmethod
    def plot_flow_vs_time(cls, time_data: List[float], flow_rate: List[float], filename: str = "flow_rate.png") -> str:
        cls.setup()
        plt.figure(figsize=(10, 6))
        plt.plot(time_data, flow_rate, linewidth=2, color='#ff7f0e', label='Exit Flow Rate')
        
        plt.title('Flow Rate vs Time', fontsize=14)
        plt.xlabel('Time (s)', fontsize=12)
        plt.ylabel('Agents / second', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        plt.tight_layout()
        
        path = os.path.join(cls.OUTPUT_DIR, filename)
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    @classmethod
    def plot_exit_utilization(cls, exit_labels: List[str], exit_counts: List[int], filename: str = "exit_utilization.png") -> str:
        cls.setup()
        plt.figure(figsize=(8, 6))
        bars = plt.bar(exit_labels, exit_counts, color='#2ca02c', alpha=0.8)
        
        plt.title('Exit Utilization Analysis', fontsize=14)
        plt.xlabel('Exit ID', fontsize=12)
        plt.ylabel('Total Agents Evacuated', fontsize=12)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                     f'{int(height)}', ha='center', va='bottom')
                     
        plt.tight_layout()
        path = os.path.join(cls.OUTPUT_DIR, filename)
        plt.savefig(path, dpi=300)
        plt.close()
        return path

    @classmethod
    def plot_density_heatmap_2d(cls, grid_x: List[float], grid_y: List[float], counts: List[float], filename: str = "density_heatmap.html") -> str:
        """Generates an interactive Plotly heatmap for agent density distributions."""
        cls.setup()
        
        # Use simple scatter interpolation or 2D histogram
        fig = go.Figure(data=go.Histogram2dContour(
            x=grid_x,
            y=grid_y,
            z=counts,
            colorscale='YlOrRd',
            contours=dict(showlabels=True, labelfont=dict(family='Raleway', color='white'))
        ))
        
        fig.update_layout(
            title="Spatial Density Heatmap (Agent Congestion)",
            xaxis_title="X Coordinate (m)",
            yaxis_title="Z Coordinate (m)",
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        path = os.path.join(cls.OUTPUT_DIR, filename)
        fig.write_html(path)
        return path
