# CPU Scheduling Algorithm Simulator

## Project Title
CPU Scheduling Algorithm Simulator

## Team Information
- Team Number: 02
- Member 1: Chan Archvathanak
- Member 2: Chhit Sovathana
- Member 3: =Am Vathanak

## Project Objective
The objective of this project is to understand how CPU scheduling works in an operating system by simulating different scheduling algorithms. This simulator implements FCFS, SJF, SRT, Round Robin, and MLFQ, and compares their performance using Waiting Time, Turnaround Time, and Response Time.

## Algorithms Implemented
- First Come First Served (FCFS)
- Shortest Job First (SJF) – Non-preemptive
- Shortest Remaining Time (SRT) – Preemptive
- Round Robin (RR) – Configurable quantum
- Multilevel Feedback Queue (MLFQ)

## Features
- Process input with:
  - Process ID
  - Arrival Time
  - Burst Time
  - Optional Priority
- Supports input from:
  - Manual input
  - CSV file
  - JSON file
- Displays:
  - Gantt Chart
  - Waiting Time
  - Turnaround Time
  - Response Time
  - Average values for all metrics
- Comparison of scheduling algorithms
- Export results option

## Technology Stack
- Language: Python
- UI: Tkinter / Console
- File Handling: CSV, JSON

## Sample Scenario
The required sample scenario used in this project is:

- P1: Arrival = 0, Burst = 5
- P2: Arrival = 1, Burst = 3
- P3: Arrival = 2, Burst = 8
- P4: Arrival = 3, Burst = 6

For Round Robin and MLFQ:
- Quantum = 2

For MLFQ:
- Queue 1 = RR, quantum 2
- Queue 2 = RR, quantum 4
- Queue 3 = FCFS

## How to Run the Project

### 1. Clone the repository
```bash
git clone https://github.com/Vathanakchanarch/OS-CPU-Scheduling-Team2.git
cd OS-CPU-Scheduling-Team2

### 2. 
