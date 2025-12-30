# Troubleshooting

## **Overview**

The document outlines the steps to diagnose and resolve the issues encountered during the deployment of the project

## **Problems**

### [SOLVED] The services is inactive (dead)

Description: When we re-deploy multiple times, the service is inactive (dead) like the following

```
root@friend-probe:~$ systemctl status probe-collector.service
○ probe-collector.service - Probe Collector
     Loaded: loaded (/etc/systemd/system/probe-collector.service; disabled; preset: enabled)
     Active: inactive (dead)
root@friend-probe:~$ systemctl status probe-agent.service
○ probe-agent.service - Probe Agent
     Loaded: loaded (/etc/systemd/system/probe-agent.service; disabled; preset: enabled)
     Active: inactive (dead)
root@friend-probe:~$
```

Workaround: Re-deploy the application again by `restart` command
