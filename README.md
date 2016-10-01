Here's a quick walkthough for managing monitoring operations through salt events. The requirement are:
- new machines will be added to monitoring
- applying a salt state notifies monitoring system
- machine decommissioning also notifies monitoring
- doesn't conflict with upstream formulas or require rewriting all states

Our solution has been to create a monitoring_extensions state that extends upstream formulas to add the appropriate events and to record the appropriate monitoring templates/checks in a grain list.

It works as follows...
We currently use Zabbix for monitoring. Zabbix has a pretty good API and there's existing modules shipped by salt to talk to it. Thus by configuring the username, password, and url in a pillar and making that pillar available to our Zabbix master, we are able to saltly talk to Zabbix.

##### New Host
So for the first task of adding a new host to Zabbix, it is pretty easy. There is already a [zabbix formula](https://github.com/saltstack-formulas/zabbix-formula) which handles the agent install. So in our monitoring_extensions state, we just include the zabbix.agent state, then fire off a salt event whenever the package is installed or updated. (I don't think we have a way of triggering only on fresh package install, so we are raising unnecessary events on upgrades, but that seems mostly harmless)

```
include:
  - zabbix.agent

notify-new-zab-node:
  event.wait:
    - name: dnb/monitoring/newhost
    - data:
      ip_address: {{ grains['ipv4'] | first() }}
      default_group: 2
    - watch:
      - pkg: zabbix-agent
```

Now that we have an event, we now need a salt reactor to pickup that event and run our add_host job. The easiest thing here, is to kickoff an orchestrate job to connect to our Zabbix master and add the host with the salt module.
```
zabbix_add_new_host:
  runner.state.orchestrate:
    - mods: orchestrations.monitoring_newhost
    - pillar:
        event_data: {{ data | json() }}
```
```
{% set data = salt.pillar.get('event_data') %}

zabbix_add_new_host:
  salt.function:
    - name: zabbix.host_create
    - tgt: 'ec2_tags:Name:ZabbixServer'
    - expr_form: grain
    - kwarg:
        host: {{ data['id'] }}
        groups: {{ data['data']['default_group'] }}
        interfaces: { type: 1, main: 1, useip: 1, ip: {{ data['data']['ip_address'] }}, dns: "", port: 10050 }
```

Looking good. So all together, when a new host comes up, the zabbix.agent state installs zabbix-agent. This triggers an event on the salt message bus and passes along IP info. This event is then passed through a reactor, which kicks off an orchestrate job to trigger the salt module for [zabbix.host_create](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.zabbix.html#salt.modules.zabbix.host_create).

##### Add Templates
The next step is to associate Zabbix templates with the host. So if salt applies the apache state, we want apache monitored by Zabbix. Again, since we don't want to fork upstream formulas, we can use the extend pattern to raise events. In this scenario, we've made things a little bit more complicated by recording the appropriate Zabbix template names into a grain on the host.
```
include:
  - openssh.banner

Add_monitor_linux:
  grains.list_present:
    - name: monitoring_groups
    - value: 'Template OS Linux'
    - watch:
      - file: /etc/ssh/banner

Update_monitor_linux:
  event.wait:
    - name: dnb/monitoring/groupchange
    - watch:
      - grains: monitoring_groups
```
In this case, we chose the completely arbitrary openssh.banner state to mark this machine as a linux host. This is a file that will likely be applied only once, as it is not often updated. So in our monitoring_extensions/linux.sls state, we watch the /etc/ssh/banner file for updates and ensure that the value 'Template OS Linux' is added as a list to the key 'monitoring_groups'. Should it ever come up in the future, this gives us an easy way to quickly match all linux hosts in our environment. (This specific case isn't that handy as there are existing grains that we could use for a 'linux' match, but this would be more useful to say quickly identify, say, apache, zookeeper, hadoop namenode, or other monitoring items).

Furthermore, we can export the grain using the salt pillar, allowing our Zabbix master to lookup what templates should be applied to the host.
```
mine_functions:
  monitoring_groups:
    - mine_function: grains.get
    - monitoring_groups
```

Now that we have the made changes to the grain, we can then watch for those updates and again raise an event.
```
zabbix_update_host_templates:
  runner.state.orchestrate:
    - mods: orchestrations.monitoring_update_template
    - pillar:
        event_data: {{ data | json() }}
```
Again we watch for that event, and have a reactor kick off an orchestrate job

```
{% set data = salt.pillar.get('event_data') %}

minion_update_mine:
  salt.function:
    - name: mine.update
    - tgt: {{ data['id'] }}

zabbix_host_templates:
  salt.function:
    - name: cmd.run
    - tgt: 'ec2_tags:Name:ZabbixServer'
    - expr_form: grain
    - arg:
      - /usr/local/bin/zabbix_template_update.py {{ data['id'] }}
```
This time our orchestrate job runs a command on the Zabbix server. This [python script](monitoring_extensions/files/zabbix_template_update.py) uses the existing salt code to access the Zabbix API. This is helpful as it then uses the same credentials and connection string specified in the salt pillar used by the rest of our salt calls. The script takes a salt minion name, looks up that name in Zabbix to get a host-id. Then it queries the salt mine for what templates should be applied to that host, and updates the host record in Zabbix.

At this stage we now have added the host to Zabbix when the agent is installed. Then for every state which sets up a monitor-able service, registers that name as a grain, then notifies the Zabbix server to add those templates to the host as they are applied.


##### Decomissioning
In our environment we mostly use AWS. Since salt has the [SQS engine](https://docs.saltstack.com/en/latest/ref/engines/all/salt.engines.sqs_events.html), we just listen for the AWS issued machine going away events, then remove the minion from salt, Zabbix, and AD.

##### Wrap-up
All in all, this seems to work pretty well. Machines are kept in sync in Zabbix and adding additional monitoring templates to a machine is as easy as adding the grains.list_present boilerplate to the state. 

