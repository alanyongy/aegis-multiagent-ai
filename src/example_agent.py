# Alan Yong Tutorial 4 30105707
# Andy Tran Tutorial 1 30125341
# Ben Foster Tutorial 1 30094638
# CPSC 383 Winter 2025 Assignment 3

from typing import override
import heapq

# If you need to import anything, add it to the import below.
from aegis import (
    END_TURN,
    SEND_MESSAGE_RESULT,
    MOVE,
    OBSERVE_RESULT,
    PREDICT_RESULT,
    SAVE_SURV,
    SAVE_SURV_RESULT,
    SEND_MESSAGE,
    TEAM_DIG,
    AgentCommand,
    AgentID,
    AgentIDList,
    Direction,
    Rubble,
    Survivor,
    OBSERVE,
    create_location,
    SLEEP
)
from a3.agent import BaseAgent, Brain, AgentController

'''
Description:
    Class to store information about a specific cell to allow modelling of other agents
'''
class CellInfo:
    def __init__(self, isCharging=None, isFire=None, isKiller=None, survivors=None, topLayerRubbleAgentAmt=None, topLayerRubbleEnergy=None, lifeSignals=None, beingObserved=None):
        self.isCharging = isCharging
        self.isFire = isFire
        self.isKiller = isKiller
        self.survivors = survivors
        self.lifeSignals = lifeSignals
        self.topLayerRubbleAgentAmt = topLayerRubbleAgentAmt
        self.topLayerRubbleEnergy = topLayerRubbleEnergy
        self.beingObserved = beingObserved

'''
Description:
    Class to store information about a specific agent to allow modelling of other agents
'''
class AgentInfo:
    def __init__(self, x=None, y=None, energy=None, action=None, idled=None, destination=None):
        self.x = x
        self.y = y
        self.energy = energy
        self.action = action
        self.idled = idled
        self.destination = destination
        self.actionCost = None

class ExampleAgent(Brain):
    def __init__(self) -> None:
        super().__init__()
        self._agent: AgentController = BaseAgent.get_agent()

        #Initialize data structures for each agent
        self.cells = {}     #Dictionary((int x, int y), CellInfo )
        self.agents = {}    #Dictionary(int agentID, AgentInfo)
        self.survivors = [] #List of tuples (x,y) for each location with survivor(s)
        self.state = 1      #Phase of algorithm: 1 = observing and sharing information, 2 = modelling others and taking actions

        #Identifiers used for agent messages
        self.agentInfoMsgID = "agentInfo"
        self.observeDoneMsgID = "observeDone"
        self.lifeSignalsMsgID = "lifeSignals"
        self.rubbleInfoMsgID = "rubbleInfo"

    '''
    Description:
        This function is called when the agent receives a message from another agent.
        It handles the message by updating the cells, agents, and state based on the broadcasted information.
    '''
    @override
    def handle_send_message_result(self, smr: SEND_MESSAGE_RESULT) -> None:
        self._agent.log(f"{smr}")

        #Update general cell information
        if(smr.msg.startswith(self.lifeSignalsMsgID)):
            msgIDUnused, msgX, msgY, msgLifeSignalAmt, msgLifeSignalInfo, msgAgentID = smr.msg.split("|")
            self.cells[int(msgX), int(msgY)].survivors = int(msgLifeSignalAmt)
            self.cells[int(msgX), int(msgY)].lifeSignals = [int(x) for x in msgLifeSignalInfo.strip("()").split(",")]
            print(f"Lifesignals at {msgX, msgY} set to {self.cells[int(msgX), int(msgY)].lifeSignals}")
            self.agents[int(msgAgentID)].energy -= 1   #If an agent sent LifeSignal information, they would have used OBSERVE which costs 1 energy. Need key as int
        
        #Update TopLayer Rubble information
        if(smr.msg.startswith(self.rubbleInfoMsgID)):
            msgIDUnused, msgX, msgY, msgTopLayerRubbleAgentAmt, msgTopLayerRubbleEnergy = smr.msg.split("|")
            self.cells[int(msgX), int(msgY)].topLayerRubbleAgentAmt = int(msgTopLayerRubbleAgentAmt)
            self.cells[int(msgX), int(msgY)].topLayerRubbleEnergy = int(msgTopLayerRubbleEnergy)
            print(f"topLayerRubbleAgentAmt and topLayerRubbleEnergy at {msgX, msgY} set to {int(msgTopLayerRubbleAgentAmt)} and {int(msgTopLayerRubbleEnergy)}")

        #Update agent information
        if(smr.msg.startswith(self.agentInfoMsgID)): 
            msgIDUnused, msgAgentID, msgX, msgY, msgEnergy = smr.msg.split("|")
            self.agents[int(msgAgentID)] = AgentInfo(int(msgX), int(msgY), int(msgEnergy), None, False) #need key as int

        #Update state
        if(smr.msg.startswith(self.observeDoneMsgID)):
            self.state = 2              #1 = observing and sharing information, 2 = modelling others and taking actions
            print("Entered state 2")

    '''
    Description:
        This function is called when the agent receives an observation result.
        It handles the observation result by sending relevant information to other agents.
    '''
    @override
    def handle_observe_result(self, ovr: OBSERVE_RESULT) -> None:
        self._agent.log(f"{ovr}")

        topLayer = ovr.cell_info.top_layer
        print("Sending observation results to other agents")
        x = ovr.cell_info.location.x
        y = ovr.cell_info.location.y

        #Count number of life signals at location
        lifeSignalAmt = sum(1 for signal in ovr.life_signals.life_signals if signal > 0)

        self._agent.send(SEND_MESSAGE(AgentIDList(), f"{self.lifeSignalsMsgID}|{x}|{y}|{lifeSignalAmt}|{ovr.life_signals}|{self._agent.get_agent_id().id}"))

        #Send TopLayer rubble information if available
        if (isinstance(topLayer, Rubble)):
            self._agent.send(SEND_MESSAGE(AgentIDList(), f"{self.rubbleInfoMsgID}|{x}|{y}|{topLayer.remove_agents}|{topLayer.remove_energy}"))

    @override
    def handle_save_surv_result(self, ssr: SAVE_SURV_RESULT) -> None:
        self._agent.log(f"{ssr}")
        #Unused

    @override
    def handle_predict_result(self, prd: PREDICT_RESULT) -> None:
        self._agent.log(f"{prd}")
        #No thanks

    @override
    def think(self) -> None:
        print(f".\n***** Agent {self._agent.get_agent_id().id} Thinking: *****\n")

        # Retrieve the current state of the world.
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        cell = world.get_cell_at(self._agent.get_location())

        #On the first round, broadcast agent information to other agents and populate cells with information that can be acquired without OBSERVE
        if self._agent.get_round_number() == 1:
            #Send agent information
            self._agent.send(SEND_MESSAGE(AgentIDList(), f"{self.agentInfoMsgID}|{self._agent.get_agent_id().id}|{cell.location.x}|{cell.location.y}|{self._agent.get_energy_level()}"))
            #Finds all survivors, charging, fire, killer cells, populates cells, fill cells and survivors with info (turn 1 only)
            self.populateCellInfo(world)

        #State 1 of algorithm: Observe all indexes in list of survivors, broadcast rubble information
        if (self.state == 1):

            #Split up observation work according to agentID
            id = self._agent.get_agent_id().id
            round = self._agent.get_round_number()
            indexToObserve = (round-1)*7+id-1

            #Observe survivors to collect toplayer rubble and lifesignal information
            if (len(self.survivors) > indexToObserve):
                self.send_and_end_turn(OBSERVE(create_location(self.survivors[indexToObserve][0], self.survivors[indexToObserve][1])))
            else:
                #Broadcast that observing survivors is finished
                self._agent.send(SEND_MESSAGE(AgentIDList(), f"{self.observeDoneMsgID}|{self._agent.get_agent_id().id}"))
                self._agent.send(END_TURN())
            return

        #State 2 of algorithm: Model all agents to predict behaviour, update worrld and agents, send action based on modelling of self
        if self.state == 2:
            ownerID = self._agent.get_agent_id().id
            
            for agentID in self.agents: 
                if agentID == ownerID:
                    print(f"Modelling self ({ownerID}):")
                else:
                    print(f"Modelling agent {agentID}:")
                
                #If the agent is dead, model that it does not take an action
                if self.agents[agentID].energy == 0:
                    self.action = END_TURN()
                else:
                    #Model this agent's decided action and update variables as if it will carry out that action
                    self.decision(agentID)

                #If modelling self, send the decided action
                if agentID == ownerID:
                    if self.agents[ownerID].action is not None:
                        self.send_and_end_turn(self.agents[ownerID].action)

        #Send a final end turn in case this agent's action is None
        self._agent.send(END_TURN())

    #Models the decision making process of target agent (by ID)
    def decision(self, agentID):
        agent = self.agents[agentID]
        
        cell = self.get_world().get_cell_at(create_location(self.agents[agentID].x, self.agents[agentID].y))
        x = cell.location.x
        y = cell.location.y

        topLayerLifeSignal = None
        if self.cells[(x, y)].lifeSignals:
            topLayerLifeSignal = self.cells[(x, y)].lifeSignals[0]

        agent.action = None
        closestChargingLocation = None

        #Create a list of possible charging locations
        moveCostToChargingCells = []
        for location in self.cells:
            if self.cells[location].isCharging:
                moveCost = self.aStarPathfind(agentID, location)[2]
                if moveCost != None and agent.energy > moveCost:
                    moveCostToChargingCells.append((moveCost, location))

        #Sort them by move cost, giving lower move cost locations a higher priority, set closestChargingLocation
        moveCostToLocationsSorted = sorted(moveCostToChargingCells, key=lambda x: x[0])
        if len(moveCostToLocationsSorted) > 0:
            closestChargingLocation = moveCostToLocationsSorted[0][1]

        #Case: Survivor on top layer of the agent's current cell
        if topLayerLifeSignal is not None and topLayerLifeSignal != 0:
            if agent.energy >= 1:   #An agent is willing to die to save a survivor
                self.handleSurvivorCase((x,y), agentID, agent)

        #Case: Survivor buried under rubble on the agent's current cell
        elif topLayerLifeSignal is not None and topLayerLifeSignal == 0:  #LifeSignal information is only collected on cells with a survivor
            #Sub-Case: No information about toplayer rubble: Observe layer
            if self.cells[(x,y)].topLayerRubbleAgentAmt == None:
                if agent.energy > 1:
                    self.handleRubbleCaseObserve((x,y), agent, cell)
                    
            #Sub-Case: Have information about toplayer rubble: TeamDig layer
            else:
                if agent.energy > self.cells[(x,y)].topLayerRubbleEnergy:
                    self.handleRubbleCaseTeamDig((x,y), agentID, agent)
                else:
                    agent.destination = None

        #Case: Current cell does not have any survivors, path to a cell with a survivor
        else:
            #Determine best destination for agent
            agent.destination = self.determineDestination(agentID)

            #Run aStar on destination to figure out path and movecost
            _, direction, totalMoveCost = self.aStarPathfind(agentID, agent.destination)
            
            if agent.energy > totalMoveCost:
                self.handleMovementCase(agent, direction)
            else:
                agent.destination = None

        #If the agent did not end up setting an action, consider helping other agents with OBSERVE
        if str(agent.action) == str(END_TURN()):
            if agent.energy > 1:
                self.handleObserveOtherCells(agent)

        #If the agent did not end up setting an action and a charging location is available, pathfind and move to it
        if agent.action == None:
            if closestChargingLocation != None:
                self.handleChargeCase(closestChargingLocation, agentID, agent)
            else:            
                agent.destination = None


        #Print no action if no action was set by any case
        if agent.action == None:
            print("No action taken")

    '''
    Parameters:
        coordinates: (x,y) of the cell
        agentID: ID of the agent calling this function
        agent: AgentInfo object of the agent calling this function
    Returns:
        None
    Description:
        Handles the case where an agent is on a cell with a survivor.
        If an agent is already saving the survivor, do nothing.
        Otherwise, model saving the survivor and update relevant information. 
    '''
    def handleSurvivorCase(self, coordinates, agentID, agent):
        x, y = coordinates[0], coordinates[1]
    
        #Detected a previous agent saving this survivor
        if self.remainingAgentsRequired(agentID, SAVE_SURV(), 1) <= 0:
            agent.action = END_TURN()
            print("Idled, a lower ID agent is saving this survivor already")
        else:
            #Model saving the survivor
            agent.action = SAVE_SURV()
            agent.energy -= 1
            self.cells[(x,y)].survivors -=1
            del self.cells[(x,y)].lifeSignals[0]
            print(f"Saving Survivor. Popped lifesignals, now {self.cells[(x,y)].lifeSignals}")
            
            #Update survivor list if this was the last survivor on the cell
            if sum(1 for x in self.cells[(x,y)].lifeSignals if x > 0) <= 0:
                self.survivors.remove((x,y))
    
    '''
    Parameters:
        coordinates: (x,y) of the cell
        agent: AgentInfo object of the agent calling this function
        cell: CellInfo object of the cell the agent is on
    Returns:
        None
    Description:
        Handles the case where an agent is on a cell with rubble and there is no information on that rubble.
        If another agent is already observing the cell, wait to receive that information (do nothing).
        Otherwise, model observing the cell and update relevant information.
    '''
    def handleRubbleCaseObserve(self, coordinates, agent, cell):
        x, y = coordinates[0], coordinates[1]
        #If cell is being observed already, wait for message about the observation results 
        if self.cells[(x,y)].beingObserved == True:
            agent.action = END_TURN()
            print("Idled, waiting for observe result at current cell")
        else:
            #Model observing the cell
            agent.action = OBSERVE(cell.location)
            agent.energy -= 1
            agent.actionCost = 1
            self.cells[(x,y)].beingObserved = True
            print("Observing newly revealed toplayer rubble")

    '''
    Parameters:
        coordinates: (x,y) of the cell
        agentID: ID of the agent calling this function
        agent: AgentInfo object of the agent calling this function
    Returns:
        None
    Description:
        Handles the case where an agent is on a cell with rubble and there is information on that rubble.
        If enough other agent(s) are modelled to be already digging, do nothing.
        Otherwise, model digging the rubble and update relevant information.
    '''
    def handleRubbleCaseTeamDig(self, coordinates, agentID, agent):
        x, y = coordinates[0], coordinates[1]
        
        #Calculate the remaining required agents needed to successfully dig this rubble
        remainingAgentsRequired = self.remainingAgentsRequired(agentID, TEAM_DIG(), self.cells[(x,y)].topLayerRubbleAgentAmt)

        #If there are enough other agents modelled to be digging this rubble, do nothing
        if remainingAgentsRequired <= 0:
            agent.action = END_TURN()
            print("Idled, enough lower ID agents teamdigging already")
        else:
            #Model digging the rubble
            agent.action = TEAM_DIG()
            agent.energy -= 1
            agent.actionCost = self.cells[(x,y)].topLayerRubbleEnergy
            print("TeamDigging")
            
            #If this is the last unit to join the teamdig, update that the rubble is gone
            if remainingAgentsRequired == 1:
                self.cells[(x,y)].topLayerRubbleAgentAmt = None
                self.cells[(x,y)].topLayerRubbleEnergy = None
                self.cells[(x,y)].beingObserved = False
                del self.cells[(x,y)].lifeSignals[0]
                print(f"Popped lifeSignals, Now {self.cells[(x,y)].lifeSignals}")

    '''
    Parameters:
        agent: AgentInfo object of the agent calling this function
        direction: Direction the agent is moving in
    Returns:
        None
    Description:
        Model moving the agent to the destination, updating relevant information
    '''
    def handleMovementCase(self, agent, direction):
        #If the agent is was not provided a valid destination or is already at the destination, do nothing
        if agent.destination == None or agent.destination == (agent.x, agent.y):
            agent.action = None
        else:
            #Model moving
            agent.action = MOVE(direction)
            agent.x += direction.dx
            agent.y += direction.dy
            agent.energy -= self._world.get_cell_at(create_location(agent.x, agent.y)).move_cost
            print(f"Moving {direction} to destination {agent.destination}")
    
    '''
    Parameters:
        closestChargingLocation: location of the closest charging cell
        agentID: ID of the agent calling this function
        agent: AgentInfo object of the agent calling this function
    Returns:
        None
    Description:
        Handles the case where an agent needs to charge.
        If the agent has enough energy to move to the charging cell, model moving towards it.
        If it's already on a charging cell, model sleeping to gain energy.
    '''
    def handleChargeCase(self, closestChargingLocation, agentID, agent):
        #Pathfind to the charging location
        agent.destination, direction, totalMoveCost = self.aStarPathfind(agentID, closestChargingLocation)

        #If the agent is not already on the charging cell, model moving towards it
        if totalMoveCost != 0:
            agent.action = MOVE(direction)
            agent.x += direction.dx
            agent.y += direction.dy
            nextCellMoveCost = self._world.get_cell_at(create_location(agent.x, agent.y)).move_cost
            agent.energy -= nextCellMoveCost
            print(f"Moving {direction} to charging cell {agent.destination}")
        elif totalMoveCost == 0:
            #Model sleeping on the charging cell
            agent.action = SLEEP()
            agent.energy += 5
            print(f"Sleeping, new energy: {agent.energy}")
    
    '''
    Parameters:
        agent: AgentInfo object of the agent calling this function
    Returns:
        None
    Description:
        Iterates through all cells with survivors and checks if the top layer has already been observed.
        If not, the agent will model observing the cell and update relevant information.
    '''
    def handleObserveOtherCells(self, agent):
        #Iterate over all locations with survivors
        for survivorLocation in self.survivors:
            location = create_location(survivorLocation[0], survivorLocation[1])

            #Consider cases where observation isnt needed
            if self.cells[survivorLocation].topLayerRubbleAgentAmt != None:                                             #If agents already have information on top layer
                continue
            if self.cells[survivorLocation].lifeSignals != None and self.cells[survivorLocation].lifeSignals[0] > 0:    #If the top layer is a survivor
                continue
            if self.cells[survivorLocation].beingObserved == True:                                                      #If an agent has already observed this (waiting for observeResult/message)
                continue

            #Model observing the cell
            agent.action = OBSERVE(location)
            agent.energy -= 1
            agent.actionCost = 1
            self.cells[survivorLocation].beingObserved = True
            print(f"Helping agents at other cells by observing {location}")
            break

    '''
    Parameters:
        targetAgentID: ID of the agent we want to check
        action: Action that want to check if other agents are doing
        requiredNum: Number of agents required to take the action
    Returns:
        int: Remaining number of agents required to take the action
    Description:
        Returns how many agents are still needed to successfully complete the indicated action on the target agent's cell
    '''
    def remainingAgentsRequired(self, targetAgentID, action, requiredNum):
        targetAgent = self.agents[targetAgentID]
        x = targetAgent.x
        y = targetAgent.y

        if requiredNum == 0:
            requiredNum = 1

        #Iterate over all agents, counting how many of them are doing the given action on this agent's cell
        numOfLowerIDAgent = 0
        for agentID, agent in self.agents.items():
            if agent.x == x and agent.y == y:
                if agentID < targetAgentID and str(self.agents[agentID].action) == str(action):
                    numOfLowerIDAgent += 1
        
        #Returns number of agents are still needed
        return requiredNum - numOfLowerIDAgent

    '''
    Parameters:
        command: The command to be sent to the agent.
    Description:
        Sends a command to the agent and ends the turn.
    '''
    def send_and_end_turn(self, command: AgentCommand):
        self._agent.log(f"SENDING {command}")
        self._agent.send(command)
        self._agent.send(END_TURN())

    '''
    Parameters:
        world: The world object containing the grid of cells.
    Returns:
        None
    Description:
        Populates the agent's cells dictionary with information about each cell in the world.
    '''
    #Iterates through every cell in the world, populating agent's datastructures with information that can be acquired without OBSERVE
    def populateCellInfo(self, world):
        world_grid = world.get_world_grid()

        #For every cell on the map...
        for x, row in enumerate(world_grid):
            for y, cell in enumerate(row):
                #Store information on special cells
                self.cells[(x,y)] = CellInfo(cell.is_charging_cell(), cell.is_fire_cell(), cell.is_killer_cell())
                #Store information on survivors
                if cell.has_survivors:
                    self.survivors.append((x,y))
                    self.cells[(x,y)].beingObserved = True

    '''
    Parameters:
        agentID: agentID that we want to determine the destination for.
    Returns: 
        destination location (a survivor) for the agent to path to.
    Description:
        Determines a destination for the agent to path to based on lowest move cost to survivor cell.
    '''
    def determineDestination(self, targetAgentID):
        if len(self.survivors) > 0:
            
            #Create a list of possible locations for this agent to go to based on location of survivors
            moveCostToLocations = []
            for survivorLocation in self.survivors:
                moveCost = self.aStarPathfind(targetAgentID, survivorLocation)[2]
                if moveCost != None:
                    moveCostToLocations.append((moveCost, survivorLocation))

            #Sort them by distance, giving lower distance locations a higher priority
            moveCostToLocationsSorted = sorted(moveCostToLocations, key=lambda x: x[0])

            #Lower priority of each location that has no agents going to it, but the location requires two agents
            reducePriority = []
            for moveCostToLocation in moveCostToLocationsSorted:
                #Find all other agents going to this location
                otherAgentsWithThisDestination = []
                for agentID, agent in self.agents.items():
                    if agent.destination == moveCostToLocation[1] and agentID != targetAgentID:
                        otherAgentsWithThisDestination.append((agentID, moveCost))

                #If this location requires two agents, and no other agents are going there, add to the reduce priority list
                if self.cells[moveCostToLocation[1]].topLayerRubbleAgentAmt == 2 and len(otherAgentsWithThisDestination) == 0:
                    reducePriority.append(moveCostToLocation)

            #Reduce priority of each location as determined prior
            for element in reducePriority:
                moveCostToLocationsSorted.remove(element)
                moveCostToLocationsSorted.append(element)

            #Return the first location where this agent would be one of the two closest agents that are intending to go to it
            for moveCostToLocation in moveCostToLocationsSorted:
                if self.isClosestTwoAgentFromDestination(targetAgentID, moveCostToLocation[1]):
                    return moveCostToLocation[1]
                
        #No destination was found
        return None

    '''
    Parameters:
        targetAgentID: ID of the agent we want to check
        targetDestination: The destination we want to check if the agent is closest to
    Returns:
        bool: True if the agent is one of the two closest agents to the destination, False otherwise
    Description:
        Checks if the target agent is one of the two closest agents to the specified destination.
    '''
    def isClosestTwoAgentFromDestination(self, targetAgentID, targetDestination):
        #Create list with all agents with this destination
        agentsWithTargetDest = []
        for agentID, agent in self.agents.items():
            if agent.destination == targetDestination:
                moveCost = self.aStarPathfind(agentID, targetDestination)[2]
                if moveCost != None:
                    agentsWithTargetDest.append((agentID, moveCost))

        #Add this agent to the list if it isn't already
        moveCost = self.aStarPathfind(targetAgentID, targetDestination)[2]
        targetAgentEntry = (targetAgentID, moveCost)
        if moveCost != None and targetAgentEntry not in agentsWithTargetDest:
            agentsWithTargetDest.append(targetAgentEntry)

        #Sort the list by agents with the closest distance to the target destination
        agentsWithTargetDestSorted = sorted(agentsWithTargetDest, key=lambda x: x[1])
        
        #Return true if this agent is among the two closest agents to the destination
        if targetAgentID == agentsWithTargetDestSorted[0][0]:
            return True  
        if targetAgentID == agentsWithTargetDestSorted[1][0]:
            return True 
        
        return False
    
    '''
    Description:
        Heuristic function for A* pathfinding algorithm.
    '''
    def chebyshevDistance(self, goal, current):
        return max(abs(goal.x - current.x), abs(goal.y - current.y))
    
    '''
    Parameters:
        agentID: ID of the agent we want to pathfind for
        targetLocation: The location we want to pathfind to
    Returns:
        if able to move to targetLocation:
            tuple: (location of destination (x,y), direction to move in, total move cost to get to destination)
        if unable to move to targetLocation:
            tuple: (None, None, 0)
        if already at targetLocation:
            tuple: (None, Direction.CENTER, 0)
    Description:
        A* pathfinding algorithm to find the optimal path to the target location.
    '''
    #Determines the direction that agent should move in next
    def aStarPathfind(self, agentID, targetLocation):
        if targetLocation == None:
            return (None, None, 0)

        #Run A*, code adapted from https://www.redblobgames.com/pathfinding/a-star/introduction.html
        cost_so_far = dict()
        came_from = dict()
        frontier = []
        
        world = self.get_world()
        agent_location= create_location(self.agents[agentID].x, self.agents[agentID].y)
        
        start = world.get_cell_at(agent_location)
        heapq.heappush(frontier, (0, agent_location))                               #Start frontier at agent location                                   
        came_from[start] = None
        cost_so_far[start] = 0
        
        while frontier:
            current = world.get_cell_at(heapq.heappop(frontier)[1])                 #Examine next highest priority node in frontier
            
            destX, destY = targetLocation
            destination = world.get_cell_at(create_location(destX, destY))

            if current == destination:                                      #If node contains survivor, all possibly optimal paths have been exhausted
               break                                                                #came_from now contains the optimal path to the survivor

            for dir in Direction:                                                   #Examine each node adjacent to frontier node
                 next = world.get_cell_at(current.location.add(dir))
                 if next == None or next.is_fire_cell() or next.is_killer_cell():   #Ignore cells that aren't valid to walk through
                     continue
                 new_cost = cost_so_far[current] + next.move_cost                   #Calculate total cost to reach this node, update frontier priorities and path as needed
                 if next not in cost_so_far or new_cost < cost_so_far[next]:
                     cost_so_far[next] = new_cost
                     priority = new_cost + self.chebyshevDistance(destination.location, next.location)
                     heapq.heappush(frontier, (priority, next.location))
                     came_from[next] = current

        #Retrace the path to determine the next cell to move to
        current = destination      
        totalMoveCost = destination.move_cost

        #If no path can be found to the destination
        if current not in came_from:
            return (None, None, None)

        #If agent is already on the cell it is pathfinding to
        if destination.location == start.location:
            return (None, Direction.CENTER, 0)
        
        #Determine next cell to move to
        while came_from[current] != start:
            totalMoveCost += came_from[current].move_cost
            current = came_from[current]
        
        #Return the direction that will bring agent to that cell
        return ((destination.location.x, destination.location.y), agent_location.direction_to(current.location), totalMoveCost)