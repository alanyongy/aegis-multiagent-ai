# 📊 AEGIS Multi-Agent Rescue AI (2023)
![](writeup-assets/AEGIS_Simulation.gif)
A coordinated multi-agent AI built in Python for the University of Calgary’s CPSC383 course, designed to rescue survivors in a grid-based simulation with complex constraints like rubble removal, energy management, and limited communication.

---

### 🔧 Background
AEGIS is a multi-agent rescue simulation where multiple autonomous agents must collaborate to rescue survivors trapped in a hazardous grid world. Survivors may be trapped under rubble that requires multiple agents working simultaneously to clear, and agents have limited energy, requiring strategic use of charging stations. **Communication between agents is limited by a 1-turn delay in message passing.**

**Why it matters:**  
Effective coordination under communication constraints is challenging. The task demands agents act efficiently and collaboratively despite partial information and dynamic hazards, aiming to minimize total rescue time. 

---

### 🎯 Key Features  
- Multi-agent coordination under limited, delayed communication  
- Simulation of all agents’ future actions locally to create virtual shared memory  
- Synchronization of agent states at start of each round via a single message  
- Energy management and hazard navigation integrated into agent decision-making  
- Designed for optimal survivor rescue in minimal turns

&nbsp;
# 🧠 Implementation Overview
🤖 **Simulated Shared Memory Across Agents**

Communication between agents suffers a 1-turn delay. To overcome this, the AI synchronizes full agent state with a single message at the start of each round. Each agent then locally simulates the actions of all other agents (including themselves) in the expected action order for the remainder of the round.

This simulation creates a consistent, up-to-date view of all agents’ planned movements and decisions, effectively eliminating communication delay and enabling coordinated decision-making.

---

🎯 **Decision Logic and Agent Actions**
- Agents prioritize survivors based on proximity, rubble requirements, and danger level.  
- When rubble blocks a survivor, agents coordinate simultaneous rubble removal.  
- Energy is managed by routing agents to charging stations before depletion to avoid downtime.  
- Dynamic replanning occurs as simulated actions update predicted world state after every agent’s move.

---

💻 **Integration with AEGIS API**
- Agents implement prescribed interface methods to read world state and issue actions.  
- Uses Python data structures to maintain local agent state and simulated plans.  
- Runs within the official AEGIS client simulation environment.

---

📌 **Message Passing Protocol**
- One initial broadcast message at round start to synchronize full agent knowledge.  
- No further communication during the round; all coordination emerges from local simulation.

&nbsp;
# 📚 Technical Writeup (the interesting part!)

### 1. Simulating Other Agents’ Decisions

*Each agent locally simulates every other agent’s upcoming decisions within its own turn to circumvent communication delay.*  
> <details>
> <summary>Click to Expand</summary>
>
> At the start of each round, agents send a single synchronization message containing all known states.
>
> Each agent, on its turn, executes the following loop:
>
> - For each agent ID (including self), simulate the agent’s next action based on the synchronized shared state and updated predictions from prior simulations in the turn.
> - Update internal world model with the predicted outcome of that agent’s action.
> - Use these updated predictions to inform its own next action choice.
>
> This results in every agent having a virtually consistent and up-to-date understanding of all other agents’ planned moves, despite communication lag.
>
> This simulation-driven coordination enables precise timing for multi-agent rubble removal and energy sharing.
>
> ![](writeup-assets/AgentSimulationDiagram.png)
> </details>

### 2. Coordinated Rubble Removal & Energy Management

*Agents plan multi-turn coordinated actions to efficiently clear rubble and maintain energy levels.*  
> <details>
> <summary>Click to Expand</summary>
>
> - Agents identify rubble locations blocking survivors.
> - Simulation ensures the required number of agents arrive simultaneously to clear rubble, avoiding wasted turns.
> - Agents monitor energy reserves, preemptively routing to charging stations.
> - Simulation updates allow agents to replan if predicted energy usage or movement conflicts arise.
>
> This results in swift, uninterrupted rescue operations with minimal idle time.
> </details>

### 3. Centralized Planning Pitfalls
*Why not a centralized leader?*
> <details>
> <summary>Click to Expand</summary>
> One possible approach would have been to assign one agent to plan all agents’ actions, then distribute them via messages.
> However, due to the 1-turn delay in message passing, this would result in every agent acting on outdated information.
> 
> Furthermore, in the event that information sharing between agents is required (information regarding previously-buried rubble), the delay would be even greater - one turn to reach the leader, and another for the leader's updated orders to reach all other agents.
> For example, even if the leader perfectly planned actions for all agents in turn `t`, they would only receive their instructions in turn `t+1` — at which point the world state has already changed.
> 
> The simulation-based decentralized strategy avoids this problem entirely by giving every agent an identical, up-to-date plan from the start of each round.
> </details>
&nbsp;
# 🏆 Results & Impact

- Achieved **100% assignment score** with effective multi-agent coordination strategy.  
- Demonstrated drastically improved rescue efficiency compared to naïve communication models.  
- Eliminated the 1-turn message delay impact, enabling near real-time cooperation.  
- Provided a scalable pattern for coordination in other multi-agent systems with communication constraints.

&nbsp;
# 🧹 Caveats
⏳ **Complex Simulation Overhead**  
Local simulation of all agents’ actions requires careful management of computation time within turn limits.

---

🔄 **Assumes Accurate State Synchronization**  
Relies on accurate initial synchronization; any mismatch can propagate errors in simulation predictions.

---

⚠️ **Simplified Communication Model**  
Works well within the assignment’s message constraints but may require adaptation for more complex or noisy channels.

&nbsp;
# 🧠 Lessons Learned
⚙️ **Simulation as Coordination Mechanism**  
Using local simulation to overcome communication delays can effectively mimic shared memory in decentralized systems.

---

🤝 **Multi-Agent Collaboration Design**  
Proper sequencing and prediction of other agents’ actions is key to coordinated multi-agent behavior in dynamic, constrained environments.

---

🧩 **Balancing Accuracy and Performance**  
Careful trade-offs between simulation detail and runtime efficiency enable practical real-time decision-making in multi-agent contexts.
