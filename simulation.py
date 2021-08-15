import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from config import Configuration, config_error
from environment import build_hospital
from infection import find_nearby, infect, recover_or_die, compute_mortality,\
healthcare_infection_correction
from motion import update_positions, out_of_bounds, update_randoms,\
get_motion_parameters
from path_planning import go_to_location, set_destination, check_at_destination,\
keep_at_destination, reset_destinations, update_pops_destination
from population import initialize_population, initialize_destination_matrix,\
set_destination_bounds, save_data, save_population, Population_trackers
from visualiser import FigureSimulation, Draw, FigureSIR

#set seed for reproducibility
#np.random.seed(100)

# i'm supposed to make productive changes so this is going to be a
# productive comment. YAY!
class SimsPopulation:
    def __init__(self, Config):
        self.Config = Config
        self.init()
    @property
    def destinations(self):
        return self._destinations
    @property
    def population(self):
        return self._population
    def init(self):
        self._population = initialize_population(self.Config, self.Config.mean_age,
                                                self.Config.max_age, self.Config.xbounds,
                                                self.Config.ybounds)
        self._destinations = initialize_destination_matrix(self.Config.pop_size, 1)

    def iter_init(self, **kargs):
        self.frame = kargs['frame']
    def move(self):
        self._update_move_direction()
        self._update_move_speed()
        self._update_final_position()
    def live(self):
        self._update_infection()
        self._update_final_health_status()

        #send cured back to population if self isolation active
        #perhaps put in recover or die class
        #send cured back to population
        self.population[:,11][self.population[:,6] == 2] = 0
    def iter_end(self):
        pass

    def _update_move_direction(self):
        #check destinations if active
        #define motion vectors if destinations active and not everybody is at destination
        active_dests = len(self._population[self._population[:,11] != 0]) # look op this only once

        if active_dests > 0 and len(self._population[self._population[:,12] == 0]) > 0:
            self._population = set_destination(self._population, self._destinations)
            self._population = check_at_destination(self._population, self._destinations,
                                                   wander_factor = self.Config.wander_factor_dest,
                                                   speed = self.Config.speed)

        if active_dests > 0 and len(self._population[self._population[:,12] == 1]) > 0:
            #keep them at destination
            self._population = keep_at_destination(self._population, self._destinations,
                                                  self.Config.wander_factor)


        #out of bounds
        #define bounds arrays, excluding those who are marked as having a custom destination
        if len(self._population[:,11] == 0) > 0:
            _xbounds = np.array([[self.Config.xbounds[0] + 0.02, self.Config.xbounds[1] - 0.02]] * len(self._population[self._population[:,11] == 0]))
            _ybounds = np.array([[self.Config.ybounds[0] + 0.02, self.Config.ybounds[1] - 0.02]] * len(self._population[self._population[:,11] == 0]))
            self._population[self._population[:,11] == 0] = out_of_bounds(self._population[self._population[:,11] == 0],
                                                                        _xbounds, _ybounds)
    def _update_move_speed(self):
        #set randoms
        if self.Config.lockdown:
            if len(self.pop_tracker.infectious) == 0:
                mx = 0
            else:
                mx = np.max(self.pop_tracker.infectious)

            if len(self._population[self._population[:,6] == 1]) >= len(self._population) * self.Config.lockdown_percentage or\
               mx >= (len(self._population) * self.Config.lockdown_percentage):
                #reduce speed of all members of society
                self._population[:,5] = np.clip(self._population[:,5], a_min = None, a_max = 0.001)
                #set speeds of complying people to 0
                self._population[:,5][self.Config.lockdown_vector == 0] = 0
            else:
                #update randoms
                self._population = update_randoms(self._population, self.Config.pop_size, self.Config.speed)
        else:
            #update randoms
            self._population = update_randoms(self._population, self.Config.pop_size, self.Config.speed)

    def _update_final_position(self):
        #for dead ones: set speed and heading to 0
        self._population[:,3:5][self._population[:,6] == 3] = 0

        #update positions
        self._population = update_positions(self._population)

    def _update_infection(self):
        #find new infections
        self._population, self._destinations = infect(self._population, self.Config, self.frame,
                                                    send_to_location = self.Config.self_isolate,
                                                    location_bounds = self.Config.isolation_bounds,
                                                    destinations = self._destinations,
                                                    location_no = 1,
                                                    location_odds = self.Config.self_isolate_proportion)
    def _update_final_health_status(self):
        #recover and die
        self._population = recover_or_die(self._population, self.frame, self.Config)

class Simulation():
    #TODO: if lockdown or otherwise stopped: destination -1 means no motion
    def __init__(self, *args, **kwargs):
        #load default config data
        self.Config = Configuration(*args, **kwargs)
        self.frame = 0

        #initialize default population
        self.Population = SimsPopulation(self.Config)
        self.pop_tracker = Population_trackers()
        
        self.figure_tstep = FigureSimulation(self.Config, figsize = (5,7))
        self.drawer_tstep = Draw(self.figure_tstep)
        
    def reinitialise(self):
        '''reset the simulation'''

        self.frame = 0
        self.Population.init()
        self.pop_tracker = Population_trackers()


    def tstep(self):
        '''
        takes a time step in the simulation
        '''
        # init Population at the begin of each iteration
        self.Population.iter_init(frame = self.frame)
        # update the movement status, like headings, speed, destinations.
        self.Population.move()
        # update the results of infections, and the health conditions for people
        self.Population.live()
        # Update other information at the end of the iteration.
        self.Population.iter_end()


        #update population statistics
        self.pop_tracker.update_counts(self.Population.population)

        #visualise
        if self.Config.visualise:
            if self.Config.self_isolate and self.Config.isolation_bounds != None:
                self.drawer_tstep.draw_environmently(population = self.Population.population, pop_tracker = self.pop_tracker, frame = self.frame)
            else:
                self.drawer_tstep.draw(population = self.Population.population, pop_tracker = self.pop_tracker, frame = self.frame)


        #report stuff to console
        sys.stdout.write('\r')
        sys.stdout.write('%i: healthy: %i, infected: %i, immune: %i, in treatment: %i, \
dead: %i, of total: %i' %(self.frame, self.pop_tracker.susceptible[-1], self.pop_tracker.infectious[-1],
                        self.pop_tracker.recovered[-1], len(self.Population.population[self.Population.population[:,10] == 1]),
                        self.pop_tracker.fatalities[-1], self.Config.pop_size))

        #save popdata if required
        if self.Config.save_pop and (self.frame % self.Config.save_pop_freq) == 0:
            save_population(self.Population.population, self.frame, self.Config.save_pop_folder)
        if self.Config.save_plot:
            self.figure_tstep.save(self.frame)
            
        #run callback
        self.callback()

        #update frame
        self.frame += 1


    def callback(self):
        '''placeholder function that can be overwritten.

        By ovewriting this method any custom behaviour can be implemented.
        The method is called after every simulation timestep.
        '''

        if self.frame == 50:
            print('\ninfecting patient zero')
            self.Population.population[0][6] = 1
            self.Population.population[0][8] = 50
            self.Population.population[0][10] = 1


    def run(self):
        '''run simulation'''

        i = 0

        while i < self.Config.simulation_steps:
            try:
                self.tstep()
            except KeyboardInterrupt:
                print('\nCTRL-C caught, exiting')
                sys.exit(1)

            #check whether to end if no infecious persons remain.
            #check if self.frame is above some threshold to prevent early breaking when simulation
            #starts initially with no infections.
            if self.Config.endif_no_infections and self.frame >= 500:
                if len(self.Population.population[(self.Population.population[:,6] == 1) |
                                       (self.Population.population[:,6] == 4)]) == 0:
                    i = self.Config.simulation_steps

        if self.Config.save_data:
            save_data(self.Population.population, self.pop_tracker)

        #report outcomes
        print('\n-----stopping-----\n')
        print('total timesteps taken: %i' %self.frame)
        print('total dead: %i' %len(self.Population.population[self.Population.population[:,6] == 3]))
        print('total recovered: %i' %len(self.Population.population[self.Population.population[:,6] == 2]))
        print('total infected: %i' %len(self.Population.population[self.Population.population[:,6] == 1]))
        print('total infectious: %i' %len(self.Population.population[(self.Population.population[:,6] == 1) |
                                                          (self.Population.population[:,6] == 4)]))
        print('total unaffected: %i' %len(self.Population.population[self.Population.population[:,6] == 0]))


    def plot_sir(self, size=(6,3), include_fatalities=False,
                 title='S-I-R plot of simulation'):
        self.figure_sir = FigureSIR(self.Config, figsize = size)
        self.drawer_sir = Draw(self.figure_sir)
        self.drawer_sir.draw(pop_tracker = self.pop_tracker, include_fatalities = include_fatalities)




if __name__ == '__main__':

    #initialize
    sim = Simulation()

    #set number of simulation steps
    sim.Config.simulation_steps = 20000

    #set color mode
    sim.Config.plot_style = 'default' #can also be dark

    #set colorblind mode if needed
    #sim.Config.colorblind_mode = True
    #set colorblind type (default deuteranopia)
    #sim.Config.colorblind_type = 'deuteranopia'

    #set reduced interaction
    #sim.Config.set_reduced_interaction()
    #sim.population_init()

    #set lockdown scenario
    #sim.Config.set_lockdown(lockdown_percentage = 0.1, lockdown_compliance = 0.95)

    #set self-isolation scenario
    #sim.Config.set_self_isolation(self_isolate_proportion = 0.9,
    #                              isolation_bounds = [0.02, 0.02, 0.09, 0.98],
    #                              traveling_infects=False)
    #sim.population_init() #reinitialize population to enforce new roaming bounds

    #run, hold CTRL+C in terminal to end scenario early
    sim.run()
