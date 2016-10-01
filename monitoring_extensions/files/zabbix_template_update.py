#!/bin/python

import salt.client
import sys

if len(sys.argv) != 2:
    print("Only specify hostname")
    sys.exit(1)

host=sys.argv[1]

def _get_hostid(host=None):
    caller = salt.client.Caller()
    zab_output=caller.cmd('zabbix.host_get', host=host)
    for host in zab_output:
        return host['hostid']

def _get_current_templates(hostid=None):
    caller = salt.client.Caller()
    zab_output=caller.cmd('zabbix.host_get', hostids=hostid,
        output='[{"hostid"}]',
        selectParentTemplates='["templateid"]'
        )
    templates = []
    print(zab_output)
    for host in zab_output:
        for template in host['parentTemplates']:
            for templateid in template:
                templates.append(template['templateid'])
    return templates

def _get_monitoring_groups(host=None):
    groups = []
    caller = salt.client.Caller()
    output = caller.cmd('mine.get', host, 'monitoring_groups')
    groups = output[host]
    return groups

def _get_zabbix_templates(host=None):
    result = []
    caller = salt.client.Caller()
    zab_output=caller.cmd('zabbix.template_get',
        host=host,
        )
    for parameters in zab_output:
        result.append(parameters['templateid'])
    return result

def _set_host_templates(hostid=None, templateids=None):
    caller = salt.client.Caller()
    zab_output=caller.cmd('zabbix.host_update',
        hostid, templates=templateids
        )
    return zab_output


current_hostid=_get_hostid(host=host)
requested_template_names=_get_monitoring_groups(host=host)
requested_template_ids=_get_zabbix_templates(host=requested_template_names)
update_result=_set_host_templates(hostid=current_hostid, templateids=requested_template_ids)
if update_result is False:
    print("Update Failed")
    sys.exit(2)
else:
    print(update_result)
