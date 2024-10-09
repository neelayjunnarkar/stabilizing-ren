Synthesizing Neural Network Controllers with Closed-Loop Dissipativity Guarantees
===================================

This repository contains code for the paper "[Synthesizing Neural Network Controllers with Closed-Loop Dissipativity Guarantees](https://arxiv.org/abs/2404.07373)".

See `train_controller.py` for example usage.

## File Structure

* `models`: controller models.
  * See comments at the top of each file for further information on each model.
  * The model we present, that ensures closed-loop dissipativity, is implemented in `dissipative_simplest_RINN.py`.
  * An unconstrained recurrent implicit neural network (RINN) model is implemented in `RINN.py`.
* `envs`: plant models.
* `trainers.py`: trainers modified to include the projection step.
* `trained_controllers`: contains the parameters for the trained controllers used in the experiments in the paper. See the paper or the comments in the relevant file in the `models` folder for how to form the controller from the parameters.

### Runnable files
* `train_controller.py`: configure and train controllers.

## Setup

This code is tested with Python 3.10.
Note that the code is configured to use [Mosek](https://www.mosek.com/), which requires a license (of which an academic one is freely available).

With the appropriate python version activated (for example, using [pyenv](https://github.com/pyenv/pyenv)), use either of the following options to install dependencies.

#### Install dependencies with [Poetry](https://python-poetry.org/)

1) `poetry install`. This will install some items then error. The following commands will resolve the error.
2) `poetry run pip install setuptools==65.5.0 pip==21`
3) `poetry run pip install wheel==0.38.0`
4) `poetry run pip install gym==0.21`
5) Now run `poetry install` again.

Then, controller training can be run with `poetry run python train_controller.py`.

#### Install dependencies from `requirements.txt`

Note: this option may require installing system dependencies such as cmake, ninja-build, and compilers for C, C++, and Fortran. The poetry installation system handles these dependencies.

1) `pip install -r requirements.txt`. This will install some items then error. The following commands will resolve the error.
2) `pip install setuptools==65.5.0 pip==21`
3) `pip install wheel==0.38.0`
4) `pip install gym==0.21`
5) Now run `pip install -r requirements.txt` again.

Then, controller training can be run with `python train_controller.py`.