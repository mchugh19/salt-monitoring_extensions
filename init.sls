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
