import matplotlib.pyplot as plt
import numpy as np
from sys import argv
from collections import deque

YLIMS = {}
OUTNAME = "motivate"

plt.rcParams['font.family'] = 'DeJavu Serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['legend.fontsize'] = 'x-large'

def mape(actual, pred):
    actual, pred = np.array(actual), np.array(pred)
    return np.mean(np.abs((actual - pred) / actual)) * 100

def running_mean(x, N):
    result = []
    window = deque()
    current_sum = 0
    for val in x:
        if len(window) > N:
            removed_val = window.popleft()
            current_sum -= removed_val
        window.append(val)
        current_sum += val
        result.append(current_sum / len(window))
    return result

def read_logs(fname, instance_id=0):
    with open(fname) as f:
        lines = [line.strip() for line in f.readlines() if len(line) > 5]

    log = []
    for line in lines:
        if "Initialized" in line or "apto::optimize]" not in line or "performance" not in line:
            continue
        line = line.split("apto::optimize]")[1].strip().split(",")
        measures = parse_measures(line)
        if measures["instance"] != instance_id:
            continue
        log.append(measures)

    return log

def parse_measures(line):
    measures = {}
    for entry in line:
        name, value = entry.strip().split(":")
        try:
            value = float(value)
        except ValueError:
            value = 0
        measures[name] = value
    return measures

def multi_comparison_time_series(prefix, files_to_plot, targets, window_size, calc_point):
    MEASURES_TO_PLOT = [
        #("uncoreFrequency", False, 0, "Uncore\nFrequency\n(Ghz)"),
        #("utilizedCoreFrequency", False, 0, "Core Frequency\n(Mhz)"),
        ("numCores", True, 0, "Number of\nCores"),
        #("hyperthreading", False, 0, "Hyperthreading"),
        ("powerConsumption", True, 1, "Power\nConsumption (W)"),
        ("appLatency", True, 0, "Latency\n(ms)"),
    ]
    MAKE_AVERAGES = ["powerConsumption", "numCores"]


    data = {}

    e_arr = []
    errors = {}
    _, axs = plt.subplots(len(MEASURES_TO_PLOT), 1, figsize=(12, 8)) #9.8, 8

    for (ax, (measure_name, plot_meaned, try_module, measure_label)) in zip(axs, MEASURES_TO_PLOT):
        if not measure_label:
            measure_label = measure_name
        ax.set_ylabel(measure_label, fontsize="large")

        nr_samples = float("inf")
        min_y, max_y = float("inf"), float("-inf")
        for fname, label in files_to_plot:
            if fname not in data:
                data[fname] = (read_logs(prefix + "/" + fname), read_logs(prefix + "/" + fname, 1))

            if not data[fname][try_module]:
                try_module = 1 - try_module

            if measure_name in data[fname][try_module][0]:
                dp = data[fname][try_module]
            else:
                dp = data[fname][1 - try_module]  # We're assuming that we only have modules 0 and 1

            raw_values = [e[measure_name] for e in dp]
            measure_values = [e[measure_name] for e in dp]

            if measure_name == "appLatency" or measure_name == "powerConsumption":
                measure_values = np.array(measure_values) / 1_000_000

            if plot_meaned:
                measure_values = running_mean(measure_values, window_size)

            ax.plot(measure_values, label=label, linewidth="2")

            if measure_name == "appLatency":
               tname="C"
            elif measure_name == "powerConsumption":
               tname="B"
            elif measure_name == "numCores":
               tname="A"
            ax.set_title(tname, x=0.96, y=1.0, pad=-16, fontweight='bold', 
                         fontsize="xx-large")
	    
            ax.axvline(x=200, color='black')
            ax.axvline(x=400, color='black')
            ax.axvline(x=600, color='black')

            nr_samples = min(nr_samples, len(measure_values))
            min_y, max_y = min(min_y, min(measure_values[calc_point:])), max(max_y, max(measure_values[calc_point:]))

            measurement_subset = measure_values[calc_point:]

            if measure_name == "appLatency":
                print(label, np.mean(raw_values[calc_point:]) / 1_000_000,
                      np.percentile(raw_values[calc_point:], 95) / 1_000_000,
                      np.percentile(raw_values[calc_point:], 99) / 1_000_000)

            if measure_name in targets:
                key = measure_name + "(MAPE)"
                execution_error = round(mape(np.zeros(len(measurement_subset)) + targets[measure_name], measurement_subset), 3)
                e_arr.append((label, execution_error))
                # print(label, execution_error)
                errors[key] = errors.get(key, []) + [f"{label}: {execution_error}"]
            if measure_name in MAKE_AVERAGES:
                key = measure_name + "(MEAN)"
                average_value = round(np.mean(measurement_subset), 3)
                errors[key] = errors.get(key, []) + [f"{label}: {average_value}"]

        if measure_name in targets:
            values = np.zeros(nr_samples) + targets[measure_name]
            ax.plot(values, color="black", alpha=0.8, label="Latency Constraint")

        if measure_name in YLIMS:
            ax.set_ylim(*YLIMS[measure_name])
        elif measure_name == "hyperthreading":
            ax.set_ylim(-0.25, 1.25)
            ax.set_yticks([0, 1], ["On", "Off"])
        else:
            if measure_name in targets:
                ax.set_ylim(min(0.6 * min_y, targets[measure_name]), max(1.1 * max_y, targets[measure_name]))
            else:
                ax.set_ylim(0.8 * min_y, 1.2 * max_y)

        ax.set_xlim(0, 2000)

        if measure_name != "appLatency":
            ax.set_xticks([], [])

    #plt.legend(bbox_to_anchor=(0.0,  6.2, 1., .102), loc=3,
    #           ncol=5, mode="expand", borderaxespad=0.,
    #           handletextpad=0.1)
    plt.legend(bbox_to_anchor=(0.0, 3.2, 1.05, 0.102), loc="best", borderaxespad=0.1, ncols=4, 
               handletextpad=0.3, mode="expand", handlelength=1.2)
    axs[-1].set_xlabel("Time-steps (Queries)", fontsize="x-large") #Updated from Application Inputs


    plt.text(100, 12, "1", ha="center", va="center", fontsize="16", 
            bbox=dict(boxstyle="circle,pad=0.5", fc="none", ec="black", lw=1.2))
    
    plt.text(300, 12, "2", ha="center", va="center", fontsize="16", 
            bbox=dict(boxstyle="circle,pad=0.5", fc="none", ec="black", lw=1.2))

    plt.text(500, 12, "3", ha="center", va="center", fontsize="16", 
            bbox=dict(boxstyle="circle,pad=0.5", fc="none", ec="black", lw=1.2))
    
    plt.text(1250, 12, "4", ha="center", va="center", fontsize="16", 
            bbox=dict(boxstyle="circle,pad=0.5", fc="none", ec="black", lw=1.2))
    
    plt.subplots_adjust(hspace=0.025)
    #plt.tight_layout()

    plt.savefig(f"{prefix}/{OUTNAME}.png", bbox_inches="tight")

    plt.clf()

def main(prefix):
    files_to_plot = [
        ("sys-only", "Only System Module"),
        ("app-only", "Only Application Module"),
        ("mm", "Multi-Module"),
    ]
    targets = {
        "appLatency": 4250000 / 1_000_000
    }
    window_size = 200
    calc_point = 2000
    multi_comparison_time_series(
        prefix, files_to_plot, targets, window_size, calc_point)

if __name__ == "__main__":
    main(argv[1])
