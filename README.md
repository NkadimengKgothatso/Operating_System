#Operating Systems and System Programming

Labs, projects, and coursework for **Operating Systems and System Programming**.

## 📚 About the Course

This course covers the fundamental abstractions, mechanisms, and implementations behind modern operating systems, split across five core areas:

- **Introduction** — OS fundamentals and abstraction
- **Concurrency** — threads, locks, condition variables, semaphores
- **Scheduling** — CPU scheduling algorithms
- **Memory** — address translation, paging, swapping
- **Persistence** — filesystems and storage



## 🗂️ Repository Structure

```
.
├── labs/
│   ├── lab1-mini-os-utilities/       # Mini OS Utilities in C
│   ├── lab2-fork-process-mgmt/       # Fork and Process Management in C
│   ├── lab3-memory-translation/      # Memory Address Translation in C
│   ├── lab4-cpu-scheduling/          # CPU Scheduling in C
│   └── lab5-concurrency/             # Concurrency in C
├── projects/
│   ├── project1-witsshell/           # witsshell — custom shell implementation
│   └── project2-cpu-scheduler/       # CPU Process Scheduler
└── README.md
```

## 🧪 Labs

| # | Topic | Description |
|---|-------|-------------|
| 1 | Mini OS Utilities | Implementing basic OS utility programs in C |
| 2 | Fork & Process Management | Process creation and management using `fork()` |
| 3 | Memory Address Translation | Simulating address translation mechanisms |
| 4 | CPU Scheduling | Implementing CPU scheduling algorithms |
| 5 | Concurrency | Threads, locks, and synchronization primitives |

## 🚀 Projects

| # | Name | Description |
|---|------|-------------|
| 1 | witsshell | A custom Unix shell implementation in C |
| 2 | CPU Process Scheduler | A more advanced CPU scheduling simulator/implementation |

## 🛠️ Building & Running

Each lab/project directory contains its own source files and (where applicable) a `Makefile`. General usage:

```bash
cd labs/lab1-mini-os-utilities
make
./run
```

Adjust binary names per lab as needed — see each subfolder's own notes for specifics.

## ⚙️ Requirements

- GCC / Clang (C compiler)
- `make`
- POSIX-compliant environment (Linux/macOS, or WSL on Windows)

## 📄 Academic Integrity

This repository reflects my own coursework for COMS3010A. In line with the course's academic integrity policy, please don't copy this code for your own submissions — use it only as a reference if you're doing similar work independently.

## 📌 Notes

Content and structure loosely follow the course's tentative schedule and may be updated as new labs/projects are added throughout the semester.
