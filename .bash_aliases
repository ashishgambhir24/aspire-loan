# Environment variables
export EDITOR="$VISUAL"
export LOAN_BACKEND="loan_backend"

# Command Aliases
alias loan_backend='cd $LOAN_BACKEND'
alias dc='docker-compose'
alias container='docker exec -ti aspire-loan-django-1 /bin/bash'
alias allow_permission='( loan_backend && chmod +x start_server.sh )'
dclogs(){
    dc logs --tail=100 --follow $@
}
dcrestart(){
	dc stop $@
	dc rm -f -v $@
	dc up --build -d $@
}
