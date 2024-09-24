Synthesizing Neural Network Controllers with Closed-Loop Dissipativity Guarantees
===================================

This repository contains code for the paper "[Synthesizing Neural Network Controllers with Closed-Loop Dissipativity Guarantees](https://arxiv.org/abs/2404.07373)".

See `train_controller.py` for example usage.

## File Structure

* `envs`: plant models.
* `models`: controller models.
  * The recurrent implicit neural network (RINN) model is in `dissipative_simplest_RINN.py`.
* `trainers.py`: trainers modified to include the projection step.

### Runnable files
* `train_controller.py`: configure and train controllers.

## Setup

This code is tested with Python 3.10.10 and PyTorch 1.11.

* `poetry install`. This will install some items then error. The following commands will resolve the error.
* `poetry run pip install setuptools==65.5.0 pip==21`
* `poetry run pip install wheel==0.38.0`
* `poetry run pip install gym==0.21`
* Now run `poetry install` again 

Then, controller training can be run with `poetry run python train_controller.py`