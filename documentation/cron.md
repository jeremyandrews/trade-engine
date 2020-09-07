The following custom django admin commands need to be regularly
invoked by a cronjob:

## timeinforce

Running this command will cancel all expired orders, whose timeinforce
has passed.

The command is very efficient and can be run as frequently as we like.
It should be run at least every 10 minutes.

### Example
`python manage.py timeinforce`
