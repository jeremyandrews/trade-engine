FROM	centos:7
LABEL   maintainer="rgerhards@adiscon.com"

# Source: https://github.com/rsyslog/rsyslog-docker/tree/master/base/centos7

RUN     yum -y install wget \
	&& cd /etc/yum.repos.d/ \
        && wget http://rpms.adiscon.com/v8-stable/rsyslog.repo
RUN	yum -y install rsyslog \
	   rsyslog-imptcp \
	   rsyslog-imrelp \
	   rsyslog-mmjsonparse \
	   rsyslog-omrelp \
	   rsyslog-omstdout \
     rsyslog-openssl \
	&& rm /etc/rsyslog.d/listen.conf
COPY	containers/audit01/rsyslog.conf /etc/rsyslog.conf

CMD ["rsyslogd", "-n"]
