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
