# Setup
Clone this repo

For every terminal, first source bash_aliases file to use command line shortcuts, using following command

> source .bash_aliases

Make sure your docker desktop is running.

After this first we need to turn on docker containers using command - 
> dc up

or we can also use the following command - 
> dcrestart

Above command is a shortcut which is mentioned in .bash_aliases file. It could be used if any time we want to restart all containers.
This commond stops existing running container, removes its image, and build it again.

similarly we can use following command to stop a container - 
> dcstop

# Logging
Logs can be monitored using following command - 
> dclogs

# Testing
To run unit tests, we need to start docker container shell using following command - 
> container

In docker shell, run - 
> make test

# API
Postman API collection can be found in repo.

Superuser(for dashboard access), staff users(to approve loans) and other users can be created and accessed using signin/login endpoint.
These endpoints could be accessed by anyone and requires username and password and returns bearer token which could be used to authenticate other endpoints.

Link to dashboard - 
http://0.0.0.0:8000/aspire-loan/admin/

Admin dashboard could be accessed using super-user credentials.

* To create/get loan(s), use create loan/ get loan endpoints using user bearer token.
* To approve loan, use approve loan endpoint using staff bearer token.
* To make payment against a loan, use add loan payment endpoint using user bearer token.

# Additional Points - 
* Interest rate, processing fee, loan periodicity could be specified while creating loan or could be changed from loan_backend/loan_backend/constants.py file.
* Installment due date are calculated from loan approval date and not loan application date.
* Penalty system is also there, which will add penalty for overdue installments daily until installment is paid.
