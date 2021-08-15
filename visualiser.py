'''
contains all methods for visualisation tasks
'''

import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from environment import build_hospital
from utils import check_folder

class Figure:
    def __init__(self, config, figsize):
        self.config = config
        self.palette = self.config.get_palette()
        self.figsize = figsize
        self._fig = None
        self.ax_list = []
        self.set_style()

    def set_style(self):
        '''sets the plot style
        '''
        if self.config.plot_style.lower() == 'dark':
            mpl.style.use('plot_styles/dark.mplstyle')
    def build_fig(self):
        pass
    def init_fig(self):
        raise NotImplementedError
    def paint_fig(self, **kargs):
        raise NotImplementedError
    def paint_environment(self):
        raise NotImplementedError
    def draw(self):
        self.fig.show()
    def save(self, name):
        try:
            self.fig.savefig('%s/%i.png' %(self.config.plot_path, name))
        except:
            check_folder(self.config.plot_path)
            self.fig.savefig('%s/%i.png' %(self.config.plot_path, name))
    def wait(self, wait_time):
        plt.pause(wait_time)

    @property
    def fig(self):
        if self._fig == None:
            self._fig = plt.figure(figsize = self.figsize)
        return self._fig

class FigureSimulation(Figure):
    def set_style(self):
        return super().set_style()
    def build_fig(self):
        if len(self.ax_list) == 0:
            self.spec = self.fig.add_gridspec(ncols=1, nrows=2, height_ratios=[5,2])
            for i in range(2):
                self.ax_list.append(self.fig.add_subplot(self.spec[i,0]))
    def init_fig(self):
        [ax.clear() for ax in self.ax_list]
        self.ax_list[0].set_xlim(self.config.x_plot[0], self.config.x_plot[1])
        self.ax_list[0].set_ylim(self.config.y_plot[0], self.config.y_plot[1])
    def paint_fig(self, **kargs):
        population = kargs['population']
        pop_tracker = kargs['pop_tracker']
        frame = kargs['frame']

        ax1_text = ["timestep: %i"%frame, "total: %i"%len(population), ]
        #plot population segments
        for i,legend in enumerate(['healthy','infected','immune','dead']):
            extracted_data = population[population[:,6] == i][:, 1:3]
            self.ax_list[0].scatter(extracted_data[:,0],extracted_data[:,1], color = self.palette[i], s = 2, label = legend)
            ax1_text.append('%s: %i'%(legend,len(extracted_data)))
        self.ax_list[0].text(self.config.x_plot[0], 
                self.config.y_plot[1] + ((self.config.y_plot[1] - self.config.y_plot[0]) / 100), 
                " ".join(ax1_text),
                fontsize = 6)

        self.ax_list[1].set_title('number of infected')
        self.ax_list[1].text(0, self.config.pop_size * 0.05, 
                    'https://github.com/paulvangentcom/python-corona-simulation',
                    fontsize=6, alpha=0.5)
        self.ax_list[1].set_ylim(0, self.config.pop_size + 200)

        if self.config.treatment_dependent_risk:
            infected_arr = np.asarray(pop_tracker.infectious)
            indices = np.argwhere(infected_arr >= self.config.healthcare_capacity)
            self.ax_list[1].plot([self.config.healthcare_capacity for x in range(len(pop_tracker.infectious))], 'r:', label='healthcare capacity')
        
        if self.config.plot_mode.lower() == 'default':
            self.ax_list[1].plot(pop_tracker.infectious, color=self.palette[1])
            self.ax_list[1].plot(pop_tracker.fatalities, color=self.palette[3], label='fatalities')
        elif self.config.plot_mode.lower() == 'sir':
            self.ax_list[1].plot(pop_tracker.susceptible, color=self.palette[0], label='susceptible')
            self.ax_list[1].plot(pop_tracker.infectious, color=self.palette[1], label='infectious')
            self.ax_list[1].plot(pop_tracker.recovered, color=self.palette[2], label='recovered')
            self.ax_list[1].plot(pop_tracker.fatalities, color=self.palette[3], label='fatalities')
        else:
            raise ValueError('incorrect plot_style specified, use \'sir\' or \'default\'')
        self.ax_list[1].legend(loc = 'best', fontsize = 6)
    def paint_environment(self):
        if self.config.self_isolate and self.config.isolation_bounds != None:
            build_hospital(self.config.isolation_bounds[0], self.config.isolation_bounds[2],
                            self.config.isolation_bounds[1], self.config.isolation_bounds[3], self.ax_list[0],
                            addcross = False)

        

class FigureSIR(Figure):
    def build_fig(self):
        if len(self.ax_list) == 0:
            self.ax_list.append(self._fig.add_subplot())
    def init_fig(self):
        [ax.clear() for ax in self.ax_list]
    def paint_fig(self, **kwargs):
        
        pop_tracker = kwargs['pop_tracker']
        #plot the thing
        self.ax_list[0].title('S-I-R plot of simulation')    
        self.ax_list[0].plot(pop_tracker.susceptible, color=self.palette[0], label='susceptible')
        self.ax_list[0].plot(pop_tracker.infectious, color=self.palette[1], label='infectious')
        self.ax_list[0].plot(pop_tracker.recovered, color=self.palette[2], label='recovered')
        if kwargs['include_fatalities']:
            self.ax_list[0].plot(pop_tracker.fatalities, color=self.palette[3], label='fatalities')   
        #add axis labels
        self.ax_list[0].xlabel('time in hours')
        self.ax_list[0].ylabel('population')
        #add legend
        self.fig.legend()
        #beautify
        self.fig.tight_layout()

class Draw:
    def __init__(self, figure:Figure):
        self._figure = figure
    def draw_environmently(self, population = None, pop_tracker = None, frame = None):
        self._figure.build_fig()
        self._figure.init_fig()
        self._figure.paint_fig(population = population, pop_tracker = pop_tracker, frame = frame)
        self._figure.paint_environment()
        self._figure.draw()

        self.save_fig(frame)
    def draw(self,population = None, pop_tracker = None, frame = None):
        self._figure.build_fig()
        self._figure.init_fig()
        self._figure.paint_fig(population = population, pop_tracker = pop_tracker, frame = frame)
        self._figure.draw()
