# [FluCalc](http://flucalc.ase.tufts.edu/)
MSS-MLE (Ma-Sandri-Sarkar Maximum Likelihood Estimator) calculator for Luria–Delbrück fluctuation analysis.

## Reference
Radchenko et. al, 2017 (Methods in Molecular Biology).  
[DOI: 10.1007/978-1-4939-7306-4_29][1]

## Installation
1. Clone or [download](https://github.com/bondarevts/flucalc/archive/master.zip) source code.
2. Install Python 3.8 or upper and libraries:
  * gunicorn=20.0.4
  * flask=1.1.1
  * flask-wtf=0.14.3
  * scipy=1.4.1
  * numpy=1.18.1

3. Set FLUCALC_SECRET_KEY environment variable with a secret string. You can use any random sequence for it.
4. Change dir to the root of source code. 
5. Start the server for FluCalc:

        gunicorn -w 4 -b <ip>:<port> flucalc:app
        
  Or you can use run_server.py script as alternative way to start the server:
       
      ./run_server.py <ip>:<port>
        
6. For shutdown server press Ctrl + C in the terminal.


[1]: https://link.springer.com/protocol/10.1007%2F978-1-4939-7306-4_29