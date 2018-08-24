# [FluCalc](http://flucalc.ase.tufts.edu/)
MSS-MLE (Ma-Sandri-Sarkar Maximum Likelihood Estimator) calculator for Luria–Delbrück fluctuation analysis.

## Reference
Radchenko et. al, 2017 (Methods in Molecular Biology).  
DOI: 10.1007/978-1-4939-7306-4_29

## Installation
1. Clone or [download](https://github.com/bondarevts/flucalc/archive/master.zip) source code.
2. Install Python 3.4 or upper and libraries:
  * gunicorn=19.1
  * flask=0.10
  * flask-wtf=0.11
  * scipy=0.17.1
  * numpy=1.11

3. Create file keys.py in the root of source code from template keys.py.template. Change the secret key string. You can use any random sequence for it.
4. Change dir to the root of source code. 
5. Start the server for FluCalc:

        gunicorn -w 4 -b <ip>:<port> flucalc.server:app
        
  Or you can use run_server.py script as alternative way to start the server:
       
      ./run_server.py <ip>:<port>
        
6. For shutdown server press Ctrl + C in the terminal.
