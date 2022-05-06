import logging
import os


## Add the verbose logging level
def verbose(message, *args, **kwargs):
	if not logging.root.isEnabledFor(logging.VERBOSE):
		return

	logging.log(logging.VERBOSE, message, *args, **kwargs)

setattr(logging, 'verbose', verbose)
setattr(logging, 'VERBOSE', 15)
logging.addLevelName(15, 'VERBOSE')


## Get log level from environment if possible
env_log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()


## Make sure the level from the environment is valid
try:
	log_level = getattr(logging, env_log_level)

except AttributeError:
	log_level = logging.INFO


## Set logging config
logging.basicConfig(
	level = log_level,
	format = "[%(asctime)s] %(levelname)s: %(message)s",
	handlers = [logging.StreamHandler()]
)
