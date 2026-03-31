from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import List, Dict, Tuple, Optional
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import json
import copy


@dataclass
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0
    remaining: int = field(init=False)
    completion: Optional[int] = field(default=None)
    first_start: Optional[int] = field(default=None)

    def __post_init__(self):
        self.remaining = self.burst


@dataclass
class SimulationResult:
    algorithm: str
    gantt: List[Tuple[int, int, str]]
    metrics: List[Dict[str, int]]
    averages: Dict[str, float]
    throughput: float
    total_time: int
    current_job: str


# -----------------------------
# Utility functions
# -----------------------------

def clone_processes(processes: List[Process]) -> List[Process]:
    return copy.deepcopy(processes)


def pid_sort_key(pid: str):
    digits = "".join(ch for ch in pid if ch.isdigit())
    return (int(digits) if digits else 10**9, pid)


def normalize_gantt(timeline: List[str]) -> List[Tuple[int, int, str]]:
    if not timeline:
        return []
    gantt = []
    start = 0
    current = timeline[0]
    for t in range(1, len(timeline)):
        if timeline[t] != current:
            gantt.append((start, t, current))
            start = t
            current = timeline[t]
    gantt.append((start, len(timeline), current))
    return gantt


def compute_metrics(processes: List[Process]) -> Tuple[List[Dict[str, int]], Dict[str, float]]:
    rows = []
    total_waiting = 0
    total_turnaround = 0
    total_response = 0

    for p in sorted(processes, key=lambda x: pid_sort_key(x.pid)):
        turnaround = p.completion - p.arrival if p.completion is not None else 0
        waiting = turnaround - p.burst
        response = p.first_start - p.arrival if p.first_start is not None else 0
        rows.append({
            "pid": p.pid,
            "arrival": p.arrival,
            "burst": p.burst,
            "start": p.first_start if p.first_start is not None else 0,
            "waiting": waiting,
            "remaining": p.remaining,
            "completion": p.completion if p.completion is not None else 0,
            "turnaround": turnaround,
            "response": response,
        })
        total_waiting += waiting
        total_turnaround += turnaround
        total_response += response

    n = len(processes) if processes else 1
    averages = {
        "avg_waiting": round(total_waiting / n, 2),
        "avg_turnaround": round(total_turnaround / n, 2),
        "avg_response": round(total_response / n, 2),
    }
    return rows, averages


def build_result(name: str, timeline: List[str], procs: List[Process]) -> SimulationResult:
    gantt = normalize_gantt(timeline)
    metrics, averages = compute_metrics(procs)
    total_time = len(timeline)
    throughput = round(len(procs) / total_time, 3) if total_time > 0 else 0.0
    current_job = timeline[-1] if timeline else "None"
    return SimulationResult(name, gantt, metrics, averages, throughput, total_time, current_job)


# -----------------------------
# Scheduling algorithms
# -----------------------------

def fcfs(processes: List[Process]) -> SimulationResult:
    procs = clone_processes(processes)
    procs.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))
    timeline = []
    time = 0

    for p in procs:
        while time < p.arrival:
            timeline.append("IDLE")
            time += 1
        if p.first_start is None:
            p.first_start = time
        for _ in range(p.burst):
            timeline.append(p.pid)
            p.remaining -= 1
            time += 1
        p.completion = time

    return build_result("First Come First Served", timeline, procs)


def sjf_non_preemptive(processes: List[Process]) -> SimulationResult:
    procs = clone_processes(processes)
    n = len(procs)
    completed = 0
    time = 0
    timeline = []
    done = set()

    while completed < n:
        ready = [p for p in procs if p.arrival <= time and p.pid not in done]
        if not ready:
            timeline.append("IDLE")
            time += 1
            continue

        ready.sort(key=lambda p: (p.burst, p.arrival, pid_sort_key(p.pid)))
        current = ready[0]
        if current.first_start is None:
            current.first_start = time
        for _ in range(current.burst):
            timeline.append(current.pid)
            current.remaining -= 1
            time += 1
        current.completion = time
        done.add(current.pid)
        completed += 1

    return build_result("Shortest Job First", timeline, procs)


def srt(processes: List[Process]) -> SimulationResult:
    procs = clone_processes(processes)
    n = len(procs)
    completed = 0
    time = 0
    timeline = []

    while completed < n:
        ready = [p for p in procs if p.arrival <= time and p.remaining > 0]
        if not ready:
            timeline.append("IDLE")
            time += 1
            continue

        ready.sort(key=lambda p: (p.remaining, p.arrival, pid_sort_key(p.pid)))
        current = ready[0]
        if current.first_start is None:
            current.first_start = time

        timeline.append(current.pid)
        current.remaining -= 1
        time += 1

        if current.remaining == 0:
            current.completion = time
            completed += 1

    return build_result("Shortest Remaining Time First", timeline, procs)


def round_robin(processes: List[Process], quantum: int = 2) -> SimulationResult:
    if quantum <= 0:
        raise ValueError("Quantum must be greater than 0")

    procs = clone_processes(processes)
    procs.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))
    n = len(procs)
    time = 0
    completed = 0
    i = 0
    timeline = []
    ready = deque()

    while completed < n:
        while i < n and procs[i].arrival <= time:
            ready.append(procs[i])
            i += 1

        if not ready:
            timeline.append("IDLE")
            time += 1
            continue

        current = ready.popleft()
        if current.first_start is None:
            current.first_start = time

        run_for = min(quantum, current.remaining)
        for _ in range(run_for):
            timeline.append(current.pid)
            time += 1
            current.remaining -= 1
            while i < n and procs[i].arrival <= time:
                ready.append(procs[i])
                i += 1
            if current.remaining == 0:
                break

        if current.remaining == 0:
            current.completion = time
            completed += 1
        else:
            ready.append(current)

    return build_result(f"Round Robin (q={quantum})", timeline, procs)


def mlfq(processes: List[Process], quanta: Optional[List[Optional[int]]] = None, aging_threshold: int = 8) -> SimulationResult:
    if quanta is None:
        quanta = [2, 4, None]

    procs = clone_processes(processes)
    procs.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))
    n = len(procs)
    time = 0
    completed = 0
    i = 0
    timeline = []

    queues = [deque(), deque(), deque()]
    wait_since_enqueued: Dict[str, int] = {}

    def enqueue_new_arrivals(now: int):
        nonlocal i
        while i < n and procs[i].arrival <= now:
            queues[0].append(procs[i])
            wait_since_enqueued[procs[i].pid] = now
            i += 1

    def apply_aging(now: int):
        for level in [1, 2]:
            kept = deque()
            while queues[level]:
                p = queues[level].popleft()
                if now - wait_since_enqueued.get(p.pid, now) >= aging_threshold:
                    wait_since_enqueued[p.pid] = now
                    queues[level - 1].append(p)
                else:
                    kept.append(p)
            queues[level] = kept

    while completed < n:
        enqueue_new_arrivals(time)
        apply_aging(time)

        selected_level = next((lvl for lvl in range(3) if queues[lvl]), None)
        if selected_level is None:
            timeline.append("IDLE")
            time += 1
            continue

        current = queues[selected_level].popleft()
        if current.first_start is None:
            current.first_start = time

        quantum = quanta[selected_level]
        run_for = current.remaining if quantum is None else min(quantum, current.remaining)
        used = 0

        while used < run_for:
            timeline.append(current.pid)
            time += 1
            used += 1
            current.remaining -= 1
            enqueue_new_arrivals(time)
            apply_aging(time)

            if current.remaining == 0:
                current.completion = time
                completed += 1
                break

            if selected_level > 0 and queues[0]:
                break
            if selected_level == 2 and (queues[0] or queues[1]):
                break

        if current.remaining > 0:
            new_level = min(selected_level + 1, 2) if quantum is not None and used == quantum else selected_level
            wait_since_enqueued[current.pid] = time
            queues[new_level].append(current)

    return build_result("Multilevel Feedback Queue", timeline, procs)


# -----------------------------
# File input
# -----------------------------

def load_from_json(path: str) -> List[Process]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        Process(
            pid=str(item["pid"]),
            arrival=int(item["arrival"]),
            burst=int(item["burst"]),
            priority=int(item.get("priority", 0))
        )
        for item in data
    ]


def load_from_csv(path: str) -> List[Process]:
    processes = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processes.append(
                Process(
                    pid=str(row["pid"]),
                    arrival=int(row["arrival"]),
                    burst=int(row["burst"]),
                    priority=int(row.get("priority", 0) or 0)
                )
            )
    return processes


def save_results_to_csv(path: str, result: SimulationResult):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Algorithm", result.algorithm])
        writer.writerow([])
        writer.writerow(["PID", "Arrival", "Burst", "Start", "Waiting", "Remaining", "Completion", "Turnaround", "Response"])
        for row in result.metrics:
            writer.writerow([
                row["pid"],
                row["arrival"],
                row["burst"],
                row["start"],
                row["waiting"],
                row["remaining"],
                row["completion"],
                row["turnaround"],
                row["response"],
            ])
        writer.writerow([])
        writer.writerow(["Average Waiting", result.averages["avg_waiting"]])
        writer.writerow(["Average Turnaround", result.averages["avg_turnaround"]])
        writer.writerow(["Average Response", result.averages["avg_response"]])
        writer.writerow(["Throughput", result.throughput])
        writer.writerow(["Total Time", result.total_time])


def sample_processes() -> List[Process]:
    return [
        Process("1", 0, 2),
        Process("2", 0, 1),
        Process("3", 2, 4),
        Process("4", 3, 6),
        Process("5", 10, 6),
        Process("6", 15, 11),
        Process("7", 16, 10),
        Process("8", 21, 14),
        Process("9", 25, 6),
        Process("10", 27, 10),
    ]


# -----------------------------
# GUI
# -----------------------------

class CPUSchedulingGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CPU Scheduling Algorithms Simulator")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 720)

        self.bg = "#e9e9e9"
        self.panel = "#efefef"
        self.root.configure(bg=self.bg)

        self.processes: List[Process] = []
        self.last_result: Optional[SimulationResult] = None
        self.animation_after_id = None
        self.step_index = 0

        self.color_map: Dict[str, str] = {"IDLE": "#d6d6d6"}
        self.palette = [
            "#f5b51b", "#2bb24c", "#3757ff", "#1d91f0", "#14c7b4",
            "#58d700", "#ffd400", "#ff7a00", "#1f1f25", "#2f3f48",
            "#a855f7", "#ef4444", "#06b6d4", "#84cc16", "#f97316"
        ]

        self.algorithm_var = tk.StringVar(value="FCFS")
        self.quantum_var = tk.StringVar(value="2")

        self.avg_wait_var = tk.StringVar(value="0.0")
        self.avg_turn_var = tk.StringVar(value="0.0")
        self.avg_resp_var = tk.StringVar(value="0.0")
        self.throughput_var = tk.StringVar(value="0.000")
        self.current_job_var = tk.StringVar(value="-")
        self.current_time_var = tk.StringVar(value="0")

        self._build_ui()
        self.load_sample_data()
        self.run_simulation()

    def _build_ui(self):
        outer = tk.Frame(self.root, bg=self.bg)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        top = tk.Frame(outer, bg=self.bg)
        top.pack(fill="x", pady=(0, 10))

        left_controls = tk.Frame(top, bg=self.panel, bd=1, relief="solid")
        left_controls.pack(side="left", fill="y")

        btn_grid = tk.Frame(left_controls, bg=self.panel)
        btn_grid.pack(padx=12, pady=12)

        tk.Button(btn_grid, text="Add Data", width=16, height=2, font=("Arial", 11, "bold"),
                  command=self.open_add_dialog, bg="#f0f0f0").grid(row=0, column=0, padx=4, pady=4)

        self.step_btn = tk.Button(btn_grid, text="Next Step >>", width=16, height=2, font=("Arial", 11),
                                  command=self.next_step, bg="#f0f0f0")
        self.step_btn.grid(row=0, column=1, padx=4, pady=4)

        tk.Button(btn_grid, text="Reset", width=16, height=2, font=("Arial", 11, "bold"),
                  command=self.reset_all, bg="#f0f0f0").grid(row=1, column=0, padx=4, pady=4)

        self.animate_btn = tk.Button(btn_grid, text="Animate >|", width=16, height=2, font=("Arial", 11),
                                     command=self.toggle_animation, bg="#f0f0f0")
        self.animate_btn.grid(row=1, column=1, padx=4, pady=4)

        tk.Button(btn_grid, text="Load CSV", width=16, height=2, font=("Arial", 11),
                  command=self.load_csv_file, bg="#f0f0f0").grid(row=2, column=0, padx=4, pady=4)

        tk.Button(btn_grid, text="Load JSON", width=16, height=2, font=("Arial", 11),
                  command=self.load_json_file, bg="#f0f0f0").grid(row=2, column=1, padx=4, pady=4)

        tk.Button(btn_grid, text="Export Results", width=16, height=2, font=("Arial", 11),
                  command=self.export_results, bg="#f0f0f0").grid(row=3, column=0, columnspan=2, padx=4, pady=4)

        stats = tk.Frame(top, bg=self.panel, bd=1, relief="solid")
        stats.pack(side="left", fill="both", expand=True, padx=10)

        stats_items = [
            ("Average Waiting Time :", self.avg_wait_var),
            ("Average Turnaround Time :", self.avg_turn_var),
            ("Average Response Time :", self.avg_resp_var),
            ("Throughput :", self.throughput_var),
        ]
        for r, (label, var) in enumerate(stats_items):
            tk.Label(stats, text=label, bg=self.panel, font=("Arial", 14, "bold")).grid(
                row=r, column=0, sticky="w", padx=16, pady=8
            )
            tk.Label(stats, textvariable=var, bg=self.panel, font=("Arial", 14, "bold")).grid(
                row=r, column=1, sticky="e", padx=18, pady=8
            )
        stats.grid_columnconfigure(0, weight=1)

        current = tk.Frame(top, bg=self.panel, bd=1, relief="solid")
        current.pack(side="right", fill="y")
        tk.Label(current, text="Current Job :", bg=self.panel, font=("Arial", 14, "bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(18, 10)
        )
        tk.Label(current, textvariable=self.current_job_var, bg=self.panel, font=("Arial", 14, "bold")).grid(
            row=0, column=1, sticky="e", padx=14, pady=(18, 10)
        )
        tk.Label(current, text="Current Time :", bg=self.panel, font=("Arial", 14, "bold")).grid(
            row=1, column=0, sticky="w", padx=14, pady=(4, 18)
        )
        tk.Label(current, textvariable=self.current_time_var, bg=self.panel, font=("Arial", 14, "bold")).grid(
            row=1, column=1, sticky="e", padx=14, pady=(4, 18)
        )

        # -----------------------------
        # Gantt chart moved here
        # -----------------------------
        gantt_wrap = tk.Frame(outer, bg=self.panel, bd=1, relief="solid")
        gantt_wrap.pack(fill="both", expand=False, pady=(0, 10))
        tk.Label(gantt_wrap, text="Gantt Chart", bg=self.panel, font=("Arial", 14, "bold")).pack(
            anchor="w", padx=10, pady=(8, 0)
        )
        self.gantt_canvas = tk.Canvas(gantt_wrap, bg="#f6f6f6", height=220, highlightthickness=0)
        self.gantt_canvas.pack(fill="both", expand=True, padx=8, pady=8)

        # -----------------------------
        # Algorithm line moved below Gantt chart
        # -----------------------------
        algo_bar = tk.Frame(outer, bg=self.panel, bd=1, relief="solid")
        algo_bar.pack(fill="x", pady=(0, 10))
        self.algorithms = [
            ("First Come First Served", "FCFS"),
            ("Shortest Job First", "SJF"),
            ("Shortest Remaining Time First", "SRT"),
            ("Round Robin", "RR"),
        ]
        for idx, (text, value) in enumerate(self.algorithms):
            rb = tk.Radiobutton(
                algo_bar, text=text, variable=self.algorithm_var, value=value,
                bg=self.panel, font=("Arial", 11), command=self.run_simulation
            )
            rb.pack(side="left", padx=(12 if idx == 0 else 4, 4), pady=12)

        tk.Label(algo_bar, text="Quantum :", bg=self.panel, font=("Arial", 11, "italic")).pack(
            side="left", padx=(14, 6)
        )
        quantum_spin = tk.Spinbox(
            algo_bar, from_=1, to=20, width=5, textvariable=self.quantum_var,
            command=self.run_simulation
        )
        quantum_spin.pack(side="left", padx=(0, 10), pady=10)

        tk.Button(algo_bar, text="MLFQ", font=("Arial", 11, "bold"),
                  command=self.run_mlfq, bg="#f4f4f4").pack(side="right", padx=12, pady=8)

        table_wrap = tk.Frame(outer, bg=self.panel, bd=1, relief="solid")
        table_wrap.pack(fill="both", expand=True)
        tk.Label(table_wrap, text="Jobs", bg=self.panel, font=("Arial", 14, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )

        columns = ("job", "arrive", "burst", "start", "wait", "remaining", "finish", "turnaround", "response")
        self.table = ttk.Treeview(table_wrap, columns=columns, show="headings", height=12)
        headers = {
            "job": "Job No",
            "arrive": "Arrive",
            "burst": "Burst Time",
            "start": "Start Time",
            "wait": "Wait Time",
            "remaining": "Remaining Time",
            "finish": "Finish Time",
            "turnaround": "Turnaround",
            "response": "Response",
        }
        widths = {
            "job": 80,
            "arrive": 90,
            "burst": 110,
            "start": 100,
            "wait": 100,
            "remaining": 130,
            "finish": 100,
            "turnaround": 110,
            "response": 100,
        }
        for col in columns:
            self.table.heading(col, text=headers[col])
            self.table.column(col, width=widths[col], anchor="center")
        self.table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def assign_color(self, pid: str) -> str:
        if pid not in self.color_map:
            idx = (len(self.color_map) - 1) % len(self.palette)
            self.color_map[pid] = self.palette[idx]
        return self.color_map[pid]

    def open_add_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Job")
        dialog.geometry("320x240")
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg)

        pid_var = tk.StringVar()
        arr_var = tk.StringVar()
        burst_var = tk.StringVar()
        pri_var = tk.StringVar(value="0")

        fields = [("Job No", pid_var), ("Arrive", arr_var), ("Burst Time", burst_var), ("Priority", pri_var)]
        for i, (label, var) in enumerate(fields):
            tk.Label(dialog, text=label, bg=self.bg, font=("Arial", 11)).grid(
                row=i, column=0, sticky="w", padx=16, pady=10
            )
            tk.Entry(dialog, textvariable=var, font=("Arial", 11), width=16).grid(
                row=i, column=1, padx=10, pady=10
            )

        def save_job():
            try:
                pid = pid_var.get().strip()
                arrival = int(arr_var.get().strip())
                burst = int(burst_var.get().strip())
                priority = int(pri_var.get().strip() or "0")

                if not pid:
                    raise ValueError("Job number is required")
                if any(p.pid == pid for p in self.processes):
                    raise ValueError("Job number must be unique")
                if arrival < 0 or burst <= 0:
                    raise ValueError("Arrival must be >= 0 and burst must be > 0")

                self.processes.append(Process(pid, arrival, burst, priority))
                self.processes.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))
                self.run_simulation()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Input Error", str(e), parent=dialog)

        tk.Button(dialog, text="Add", font=("Arial", 11, "bold"), command=save_job, width=12).grid(
            row=5, column=0, padx=14, pady=20
        )
        tk.Button(dialog, text="Cancel", font=("Arial", 11), command=dialog.destroy, width=12).grid(
            row=5, column=1, padx=14, pady=20
        )

    def load_csv_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if path:
            try:
                self.processes = load_from_csv(path)
                self.processes.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))
                self.run_simulation()
            except Exception as e:
                messagebox.showerror("Load Error", str(e))

    def load_json_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            try:
                self.processes = load_from_json(path)
                self.processes.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))
                self.run_simulation()
            except Exception as e:
                messagebox.showerror("Load Error", str(e))

    def load_sample_data(self):
        self.processes = sample_processes()
        self.processes.sort(key=lambda p: (p.arrival, pid_sort_key(p.pid)))

    def reset_all(self):
        self.stop_animation()
        self.processes = []
        self.last_result = None
        self.step_index = 0
        self.avg_wait_var.set("0.0")
        self.avg_turn_var.set("0.0")
        self.avg_resp_var.set("0.0")
        self.throughput_var.set("0.000")
        self.current_job_var.set("-")
        self.current_time_var.set("0")
        for item in self.table.get_children():
            self.table.delete(item)
        self.gantt_canvas.delete("all")

    def run_mlfq(self):
        if not self.processes:
            messagebox.showinfo("No Data", "Please add or load process data first.")
            return
        self.stop_animation()
        self.step_index = 0
        self.last_result = mlfq(self.processes, [2, 4, None], aging_threshold=8)
        self.refresh_ui(self.last_result, partial=False)

    def run_simulation(self):
        if not self.processes:
            return
        try:
            self.stop_animation()
            self.step_index = 0

            algo = self.algorithm_var.get()
            q = int(self.quantum_var.get().strip() or "2")

            if algo == "FCFS":
                result = fcfs(self.processes)
            elif algo == "SJF":
                result = sjf_non_preemptive(self.processes)
            elif algo == "SRT":
                result = srt(self.processes)
            elif algo == "RR":
                result = round_robin(self.processes, q)
            else:
                result = fcfs(self.processes)

            self.last_result = result
            self.refresh_ui(result, partial=False)
        except Exception as e:
            messagebox.showerror("Simulation Error", str(e))

    def refresh_ui(self, result: SimulationResult, partial: bool = False):
        self.avg_wait_var.set(str(result.averages["avg_waiting"]))
        self.avg_turn_var.set(str(result.averages["avg_turnaround"]))
        self.avg_resp_var.set(str(result.averages["avg_response"]))
        self.throughput_var.set(str(result.throughput))
        self.current_job_var.set(result.current_job)
        self.current_time_var.set(str(result.total_time))

        ordered = sorted(result.metrics, key=lambda r: pid_sort_key(r["pid"]))
        for item in self.table.get_children():
            self.table.delete(item)

        for row in ordered:
            self.table.insert("", "end", values=(
                row["pid"], row["arrival"], row["burst"], row["start"],
                row["waiting"], row["remaining"], row["completion"],
                row["turnaround"], row["response"]
            ))

        self.draw_gantt(result.gantt, result.total_time, visible_segments=None if not partial else self.step_index)

    def draw_gantt(self, gantt: List[Tuple[int, int, str]], total_time: int, visible_segments: Optional[int] = None):
        canvas = self.gantt_canvas
        canvas.delete("all")
        canvas.update_idletasks()

        width = max(canvas.winfo_width(), 1000)
        if not gantt or total_time <= 0:
            return

        if visible_segments is not None:
            gantt = gantt[:visible_segments]

        left = 14
        top = 28
        bar_h = 48
        row_gap = 78
        usable_width = width - 28
        unit = max(20, usable_width / max(total_time, 1))

        current_x = left
        current_row = 0
        wrap_limit = left + usable_width

        for idx, (start, end, pid) in enumerate(gantt):
            duration = end - start
            segment_width = max(unit * duration, 28)

            if current_x + segment_width > wrap_limit:
                current_row += 1
                current_x = left

            y = top + current_row * row_gap
            color = self.assign_color(pid)

            canvas.create_rectangle(
                current_x, y, current_x + segment_width, y + bar_h,
                fill=color, outline="white", width=2
            )

            if segment_width >= 30:
                text_color = "white" if pid != "IDLE" else "black"
                canvas.create_text(
                    current_x + segment_width / 2, y + bar_h / 2,
                    text=pid, fill=text_color, font=("Arial", 10, "bold")
                )

            canvas.create_text(
                current_x, y + bar_h + 14, text=str(start),
                anchor="w", fill="#444", font=("Arial", 9)
            )

            if idx == len(gantt) - 1:
                canvas.create_text(
                    current_x + segment_width, y + bar_h + 14, text=str(end),
                    anchor="e", fill="#444", font=("Arial", 9)
                )

            current_x += segment_width

    def next_step(self):
        if not self.last_result or not self.last_result.gantt:
            return

        if self.step_index < len(self.last_result.gantt):
            self.step_index += 1
            self.draw_gantt(self.last_result.gantt, self.last_result.total_time, visible_segments=self.step_index)

            current_seg = self.last_result.gantt[self.step_index - 1]
            self.current_job_var.set(current_seg[2])
            self.current_time_var.set(str(current_seg[1]))

    def animate_step(self):
        if not self.last_result or self.step_index >= len(self.last_result.gantt):
            self.stop_animation()
            return

        self.next_step()
        self.animation_after_id = self.root.after(700, self.animate_step)

    def toggle_animation(self):
        if self.animation_after_id is None:
            if not self.last_result:
                return
            self.step_index = 0
            self.draw_gantt([], self.last_result.total_time, visible_segments=0)
            self.current_job_var.set("-")
            self.current_time_var.set("0")
            self.animate_btn.config(text="Stop")
            self.animate_step()
        else:
            self.stop_animation()

    def stop_animation(self):
        if self.animation_after_id is not None:
            self.root.after_cancel(self.animation_after_id)
            self.animation_after_id = None
        self.animate_btn.config(text="Animate >|")

    def export_results(self):
        if not self.last_result:
            messagebox.showinfo("No Results", "Run a simulation first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if path:
            try:
                save_results_to_csv(path, self.last_result)
                messagebox.showinfo("Export Complete", f"Results saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))


def main():
    root = tk.Tk()
    app = CPUSchedulingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()