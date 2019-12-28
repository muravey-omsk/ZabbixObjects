# Проект ZabbixObjects
Модуль python3 для работы с Zabbix API через ООП

## Требования
1. Системные приложения
: `python3`
2. Модули python3
: `py-zabbix`

## Примеры использования

```python
from pyzabbix import ZabbixAPI
from ZabbixObjects.Zabbix import ZabbixHost

zabbix_api = ZabbixAPI('https://localhost/', user='user', password='pass')
from ZabbixObjects.ZabbixFactory import ZabbixHostFactory
zhost_factory = ZabbixHostFactory(zabbix_api)
zabbix_host = zhost_factory.get_by_name('zabbix')

```
