zabbix_add_new_host:
  runner.state.orchestrate:
    - mods: orchestrations.monitoring_newhost
    - pillar:
        event_data: {{ data | json() }}
