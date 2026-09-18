"""Swarm mode (TIEKAT-style) orchestration for EVIE.

Swarm Mode is a conservative director layer on top of EVIE's modules/workflows.
It is designed to be:

* **Local-first**: no mandatory cloud dependencies
* **Auditable**: plans and runs are stored in the existing run history tables
* **Safe by default**: it reuses artifact validation + code safety gate
"""
