mptcp
=====
To get things up and running first clone the repository:
```
git clone https://github.com/jreeseue/mptcp.git 
git submodule init 
git submodule update
```
From here mptcp will need to be setup inside of Mininet. To do this first
follow the instructions from http://github.com/bocon13/mptcp_setup. The code
for this will already be in mptcp_setup, as it is a submodule of this
project. Lastly, create copies of the test files with:
```
./createFiles.sh
```
At this point tests can be run from the src/ directory. To run the Fat Tree
tests use:
```
sudo ./test_ft.py
```
The N-switch tests can be run with:
```
sudo ./test_switch.py. <br/><br/>
```
Enjoy.
