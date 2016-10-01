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
