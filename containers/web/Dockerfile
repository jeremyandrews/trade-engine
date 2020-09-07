FROM python:3.6

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
 rsync telnet net-tools vim nginx cron

# By copying over requirements first, we make sure that Docker will cache
# our installed requirements rather than reinstall them on every build
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Configure gunicorn
RUN mkdir /etc/gunicorn && chmod 755 /etc/gunicorn
COPY web/gunicorn_config.py /etc/gunicorn/config.py
# Configure nginx
COPY web/nginx.conf /etc/nginx/nginx.conf

# Now copy in our code, and run it
COPY . /app

ADD web/timeinforce.crontab /etc/cron.d/timeinforce.crontab
RUN chmod 0644 /etc/cron.d/timeinforce.crontab
RUN /usr/bin/crontab /etc/cron.d/timeinforce.crontab

EXPOSE 8000
# Wrapper script migrates db then launches Django.
CMD ["bash", "containers/web/launch.sh"]
