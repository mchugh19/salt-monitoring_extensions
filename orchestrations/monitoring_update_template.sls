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
