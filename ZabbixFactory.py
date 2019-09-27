from abc import ABC

from ZabbixObjects.Zabbix import *


class ZabbixFactory(ABC):
    def __init__(self, zapi: ZabbixAPI):
        super().__init__()
        self._zapi = zapi


class ZabbixGroupFactory(ZabbixFactory):

    def make(self, group: dict):
        return ZabbixGroup(self._zapi, group)

    def get_by_id(self, groupid: int):
        """Создание объекта ZabbixGroup из ZabbixAPI"""
        return ZabbixGroup.get_by_id(self._zapi, groupid)

    def get_by_filter(self, _filter: dict):
        """Получение списка объектов ZabbixGroup из ZabbixAPI по фильтру"""
        hostgroup_get = dict(
            output='extend',
            filter=_filter,
        )
        z_group: list = self._zapi.hostgroup.get(**hostgroup_get)
        return [self.make(group) for group in z_group]

    def get_by_name(self, _name: str):
        """Получение списка объекторв ZabbixGroup из ZabbixAPI по имени"""
        return self.get_by_filter({'name': _name})

    def create(self, groupname: str):
        """Создание нового узлв в ZabbixAPI"""
        z_groups = self._zapi.hostgroup.create(name=groupname)
        with no_index('Ошибка создания группы'):
            return self.make(z_groups.get('groupids')[0])


class ZabbixMacroFactory(ZabbixFactory):

    def make(self, macro: dict):
        return ZabbixMacro(self._zapi, macro)

    def get_by_filter(self, _filter: dict):
        """Получение макроса из ZabbixAPI по фильтру"""
        usermacro_get = dict(
            output='extend',
            filter=_filter,
        )
        z_macros = self._zapi.usermacro.get(**usermacro_get)
        return [self.make(m) for m in z_macros]

    def create(self, hostid: int, macro: str, value: str = ''):
        """Создание нового макроса в ZabbixAPI

        :rtype: ZabbixMacro
        """
        usermacro_create = dict(
            hostid=hostid,
            macro=macro,
            value=value,
        )
        with no_index('Ошибка создания макроса'):
            z_hostmacroid = self._zapi.usermacro.create(**usermacro_create)['hostmacroids'][0]
            return self.make(dict(hostmacroid=z_hostmacroid))


class ZabbixTemplateFactory(ZabbixFactory):

    def make(self, template: dict):
        return ZabbixTemplate(self._zapi, template)

    def get_by_filter(self, _filter: dict):
        """Получение шаблона из ZabbixAPI по фильтру"""
        template_get = dict(
            output='extend',
            filter=_filter,
        )
        z_templates = self._zapi.template.get(**template_get)
        return [self.make(t) for t in z_templates]

    def get_by_name(self, template_name: str):
        """Получение шаблона из ZabbixAPI по имени"""
        return self.get_by_filter({'host': template_name})


class ZabbixInterfaceFactory(ZabbixFactory):

    def make(self, interface: dict):
        return ZabbixInterface(self._zapi, interface)

    def get_by_id(self, interfaceid: int):
        """Создание объекта ZabbixInterface из ZabbixAPI"""
        interface_get = dict(
            output='extend',
            interfaceid=interfaceid
        )
        z_interface = self._zapi.hostinterface.get(**interface_get)
        return self.make(z_interface)


class ZabbixHostFactory(ZabbixFactory):

    def make(self, host: dict):
        return ZabbixHost(self._zapi, host)

    def get_by_id(self, hostid: int):
        """Создание объекта ZabbixHost из ZabbixAPI"""
        return ZabbixHost.get_by_id(self._zapi, hostid)

    def get_by_filter(self, _filter: dict, **options):
        """Получение списка объектов ZabbixHost из ZabbixAPI по фильтру"""
        host_get = dict(
            output=options.get('output', 'extend'),
            filter=_filter,
        )
        host_get.update(options)
        z_hosts = self._zapi.host.get(**host_get)
        return [self.make(z_host) for z_host in z_hosts]

    def get_by_name(self, _name: str):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        return self.get_by_filter({'host': _name})

    def search(self, _search: dict, **options):
        """Поиск в ZabbixAPI"""
        z_hosts = self._zapi.host.get(
            output=options.get('output', 'extend'),
            search=_search,
            searchWildcardsEnabled=True,
        )
        return [self.make(host) for host in z_hosts]

    def create(self, host: dict):
        """Создание нового макроса в ZabbixAPI

        :rtype: ZabbixHost
        """
        if not host.get('host'):
            raise ValueError
        z_host = dict()
        with no_index('Ошибка создания узла'):
            z_host['hostid'] = self._zapi.host.create(**host)['hostids'][0]
            return self.make(z_host)


class ZabbixTriggerFactory(ZabbixFactory):

    def _get_host_by_triggerid(self, triggerid: int):
        with no_index('Триггер не найден'):
            z_host = self._zapi.trigger.get(
                output='hosts',
                triggerids=triggerid,
                selectHosts=['extend'],
            )[0]
            return ZabbixHost(self._zapi, z_host)

    def make(self, trigger: dict):
        host = self._get_host_by_triggerid(int(trigger['triggerid']))
        return ZabbixTrigger(host, trigger)

    def get_by_id(self, triggerid: int):
        return ZabbixTrigger.get_by_id(self._zapi, triggerid)


class ZabbixEventFactory(ZabbixFactory):

    def _get_trigger_by_eventid(self, eventid: int):
        with no_index('Событие не найдено'):
            z_event = self._zapi.event.get(
                output=['relatedObject', 'hosts'],
                eventids=eventid,
                selectRelatedObject=['extend'],
                selectHosts=['extend'],
            )[0]
            z_trigger = z_event['relatedObject']
            z_host = z_event['hosts'][0]
            host = ZabbixHost(self._zapi, z_host)
            return ZabbixTrigger(host, z_trigger)

    def make(self, event: dict):
        trigger = self._get_trigger_by_eventid(event['eventid'])
        return ZabbixEvent(trigger, event)

    def get_by_id(self, eventid: int):
        """Создание объекта ZabbixEvent из ZabbixAPI"""
        return ZabbixEvent.get_by_id(self._zapi, eventid)

    def get_by_groupids(self, groupids: list, limit: int = 500):
        """Генератор событий из групп groupids по ZabbixAPI"""
        if groupids is None:
            groupids = [10]  # Группа по-умолчанию - A4
        time_from = int(time.time()) - (3600 * 1)  # За последний час
        z_events: list = self._zapi.event.get(
            output='extend',
            groupids=groupids,
            acknowledged='false',
            suppressed='false',
            time_from=time_from,
            value=1,
            selectHosts=['hostid', 'host', 'name'],
            selectRelatedObject=['triggerid', 'description', 'value'],
            filter={'r_eventid': 0},  # только события без восстановления
            tags=[
                {'tag': 'autoticket'},
            ]
        )
        if len(z_events) >= limit:
            yield
        for event in z_events:
            yield self.make(event)
