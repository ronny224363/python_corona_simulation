'''
file that contains all function related to population mobility
and related computations
'''

import numpy as np

class Handler:

    _next_handler = None

    def set_next_handler(self):
        self._next_handler = handler
        return self._next_handler
        

    def update(self, population, destination, config):
        raise NotImplementedError

class updateDestinationHandler(Handler):
    def update(self, population, destination, config):
        active_dests = len(population[population[:,11] != 0])
        if active_dests > 0:
            if len(self.population[self.population[:,12] == 0]) > 0:
                population = set_destination(population, destinations)
                population = check_at_destination(population, destinations,
                                                       wander_factor = Config.wander_factor_dest,
                                                       speed = Config.speed)

            if len(population[population[:,12] == 1]) > 0:
                #keep them at destination
                population = keep_at_destination(population, destinations,
                                                      Config.wander_factor)
        return population

class updateDirectionHandler(Handler):
    def update(self, population, destination, config):
        if len(population[:,11] == 0) > 0:
            _xbounds = np.array([[Config.xbounds[0] + 0.02, Config.xbounds[1] - 0.02]] * len(population[population[:,11] == 0]))
            _ybounds = np.array([[Config.ybounds[0] + 0.02, Config.ybounds[1] - 0.02]] * len(population[population[:,11] == 0]))
            population[population[:,11] == 0] = out_of_bounds(population[population[:,11] == 0],
                                                                        _xbounds, _ybounds)
        return population

class updateSpeedHandler(Handler):
    def update(self, population, destination, config):
        if Config.lockdown:
            if len(pop_tracker.infectious) == 0:
                mx = 0
            else:
                mx = np.max(pop_tracker.infectious)

            if len(population[population[:,6] == 1]) >= len(population) * Config.lockdown_percentage or\
               mx >= (len(population) * Config.lockdown_percentage):
                #reduce speed of all members of society
                population[:,5] = np.clip(population[:,5], a_min = None, a_max = 0.001)
                #set speeds of complying people to 0
                population[:,5][Config.lockdown_vector == 0] = 0
            else:
                #update randoms
                population = update_randoms(population, Config.pop_size, Config.speed)
        else:
            #update randoms
            population = update_randoms(population, Config.pop_size, Config.speed)
        population[:,3:5][population[:,6] == 3] = 0
        return population

class updatePositionHandler(Handler):
    def update(self, population, destination, config):
        population = update_positions(population)
        return population



class motionApplication(Handler):
    def __init__(self):
        self._destinationHandler = updateDestinationHandler()
        self._directionHandler = updateDirectionHandler()
        self._speedHandler = updateSpeedHandler()
        self._positionHandler = updatePositionHandler()

        self._handler = self._destinationHandler.set_next_handler(self._directionHandler).set_next_handler(self._speedHandler).set_next_handler(self._positionHandler)

    def update(self, population, destination, config):
        return self._handler(population, destination, config)
    
def update_positions(population):
    '''update positions of all people

    Uses heading and speed to update all positions for
    the next time step

    Keyword arguments
    -----------------
    population : ndarray
        the array containing all the population information
    '''

    #update positions
    #x
    population[:,1] = population[:,1] + (population[:,3] * population[:,5])
    #y
    population[:,2] = population[:,2] + (population [:,4] * population[:,5])

    return population


def out_of_bounds(population, xbounds, ybounds):
    '''checks which people are about to go out of bounds and corrects

    Function that updates headings of individuals that are about to 
    go outside of the world boundaries.
    
    Keyword arguments
    -----------------
    population : ndarray
        the array containing all the population information

    xbounds, ybounds : list or tuple
        contains the lower and upper bounds of the world [min, max]
    '''
    #update headings and positions where out of bounds
    #update x heading
    #determine number of elements that need to be updated

    shp = population[:,3][(population[:,1] <= xbounds[:,0]) &
                            (population[:,3] < 0)].shape
    population[:,3][(population[:,1] <= xbounds[:,0]) &
                    (population[:,3] < 0)] = np.clip(np.random.normal(loc = 0.5, 
                                                                        scale = 0.5/3,
                                                                        size = shp),
                                                        a_min = 0.05, a_max = 1)

    shp = population[:,3][(population[:,1] >= xbounds[:,1]) &
                            (population[:,3] > 0)].shape
    population[:,3][(population[:,1] >= xbounds[:,1]) &
                    (population[:,3] > 0)] = np.clip(-np.random.normal(loc = 0.5, 
                                                                        scale = 0.5/3,
                                                                        size = shp),
                                                        a_min = -1, a_max = -0.05)

    #update y heading
    shp = population[:,4][(population[:,2] <= ybounds[:,0]) &
                            (population[:,4] < 0)].shape
    population[:,4][(population[:,2] <= ybounds[:,0]) &
                    (population[:,4] < 0)] = np.clip(np.random.normal(loc = 0.5, 
                                                                        scale = 0.5/3,
                                                                        size = shp),
                                                        a_min = 0.05, a_max = 1)

    shp = population[:,4][(population[:,2] >= ybounds[:,1]) &
                            (population[:,4] > 0)].shape
    population[:,4][(population[:,2] >= ybounds[:,1]) &
                    (population[:,4] > 0)] = np.clip(-np.random.normal(loc = 0.5, 
                                                                        scale = 0.5/3,
                                                                        size = shp),
                                                        a_min = -1, a_max = -0.05)

    return population


def update_randoms(population, pop_size, speed=0.01, heading_update_chance=0.02, 
                   speed_update_chance=0.02, heading_multiplication=1,
                   speed_multiplication=1):
    '''updates random states such as heading and speed
    
    Function that randomized the headings and speeds for population members
    with settable odds.

    Keyword arguments
    -----------------
    population : ndarray
        the array containing all the population information
    
    pop_size : int
        the size of the population

    heading_update_chance : float
        the odds of updating the heading of each member, each time step

    speed_update_chance : float
        the oodds of updating the speed of each member, each time step

    heading_multiplication : int or float
        factor to multiply heading with (default headings are between -1 and 1)

    speed_multiplication : int or float
        factor to multiply speed with (default speeds are between 0.0001 and 0.05

    speed : int or float
        mean speed of population members, speeds will be taken from gaussian distribution
        with mean 'speed' and sd 'speed / 3'
    '''

    #randomly update heading
    #x
    update = np.random.random(size=(pop_size,))
    shp = update[update <= heading_update_chance].shape
    population[:,3][update <= heading_update_chance] = np.random.normal(loc = 0, 
                                                        scale = 1/3,
                                                        size = shp) * heading_multiplication
    #y
    update = np.random.random(size=(pop_size,))
    shp = update[update <= heading_update_chance].shape
    population[:,4][update <= heading_update_chance] = np.random.normal(loc = 0, 
                                                        scale = 1/3,
                                                        size = shp) * heading_multiplication
    #randomize speeds
    update = np.random.random(size=(pop_size,))
    shp = update[update <= heading_update_chance].shape
    population[:,5][update <= heading_update_chance] = np.random.normal(loc = speed, 
                                                        scale = speed / 3,
                                                        size = shp) * speed_multiplication

    population[:,5] = np.clip(population[:,5], a_min=0.0001, a_max=0.05)
    return population


def get_motion_parameters(xmin, ymin, xmax, ymax):
    '''gets destination center and wander ranges

    Function that returns geometric parameters of the destination
    that the population members have set.

    Keyword arguments:
    ------------------
        xmin, ymin, xmax, ymax : int or float
        lower and upper bounds of the destination area set.

    '''

    x_center = xmin + ((xmax - xmin) / 2)
    y_center = ymin + ((ymax - ymin) / 2)

    x_wander = (xmax - xmin) / 2
    y_wander = (ymax - ymin) / 2

    return x_center, y_center, x_wander, y_wander
