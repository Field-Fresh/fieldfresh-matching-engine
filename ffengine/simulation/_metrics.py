from typing import Dict
import matplotlib.pyplot as plt
import seaborn as sbn
import pandas as pd

#==============================================================================================================
# Visualization functions
#==============================================================================================================

class TestCaseMetrics:
    def __init__(self, named_results: Dict[str, dict]):
        self.named_results = named_results

        tables = {}
        if len(named_results):
            for testcase in named_results:
                for metric in named_results[testcase]:
                    if not metric in tables:
                        tables[metric] =  {testcase: named_results[testcase][metric]}
                    
                    tables[metric].update( {testcase: named_results[testcase][metric]} )
        
        self.tables = {i: pd.DataFrame(t) for i,t in tables.items()}

        plt.style.use('ggplot')
        plt.ion()
    
    def surplus_plot(self, agent: str):

        assert agent in ['Buyer', 'Seller'], "agent must be buyer or seller"

        data = self.tables[agent + '-Surplus']
        bar_w = .35
        plt.figure()
        for i, comp in enumerate(data):
            plt.bar(data.index + i*bar_w, data[comp], bar_w, label=comp)

        plt.xlabel(agent.capitalize())
        plt.ylabel('Surplus')
        plt.legend()
        # plt.show()