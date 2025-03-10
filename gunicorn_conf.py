from multiprocessing import cpu_count

# Socket Path
bind = 'unix:/home/rezayogaswara/python_projects/helpdesk-router.sock'

# Worker Options
# workers = cpu_count() + 1
workers = 1
worker_class = 'uvicorn.workers.UvicornWorker'

# Logging Options
accesslog = '/home/rezayogaswara/python_projects/helpdesk-router/access_log'
errorlog = '/home/rezayogaswara/python_projects/helpdesk-router/error_log'
capture_output = True
loglevel = 'info'
reload = True
