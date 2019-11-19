from abc import ABC
from typing import Union

from .Zabbix import *


class ZabbixFactory(Zabbix, ABC):
    pass


class ZabbixProxyFactory(ZabbixFactory):
    def make(self, proxy):
        return ZabbixProxy(self._zapi, proxy)

    def get_by_name(self, _name: Union[str, List[str]]):
        """Получение списка объекторв ZabbixProxy из ZabbixAPI по имени"""
        return self.get_by_filter({'name': _name})

    @zapi_exception("Ошибка получения Zabbix прокси")
    def get_by_filter(self, _filter: dict, **options):
        """Получение списка объектов ZabbixGroup из ZabbixAPI по фильтру"""
        proxy_get = dict(
            output='extend',
            filter=_filter,
        )
        proxy_get.update(options)
        z_proxies: list = self._zapi.proxy.get(**proxy_get)
        return (self.make(proxy) for proxy in z_proxies)


class ZabbixGroupFactory(ZabbixFactory):

    def make(self, group: dict):
        return ZabbixGroup(self._zapi, group)

    def get_by_id(self, groupid: int):
        """Создание объекта ZabbixGroup из ZabbixAPI"""
        return ZabbixGroup.get_by_id(self._zapi, groupid)

    @zapi_exception("Ошибка получения Zabbix группы")
    def get_by_filter(self, _filter: dict):
        """Получение списка объектов ZabbixGroup из ZabbixAPI по фильтру"""
        hostgroup_get = dict(
            output='extend',
            filter=_filter,
        )
        z_group: list = self._zapi.hostgroup.get(**hostgroup_get)
        return (self.make(group) for group in z_group)

    def get_by_name(self, _name: Union[str, List[str]]):
        """Получение списка объекторв ZabbixGroup из ZabbixAPI по имени"""
        return self.get_by_filter({'name': _name})

    @zapi_exception("Ошибка создания Zabbix группы")
    def new(self, groupname: str):
        """Создание нового узлв в ZabbixAPI"""
        z_groups = self._zapi.hostgroup.create(name=groupname)
        return self.make({'groupid': z_groups.get('groupids')[0]})


class ZabbixMacroFactory(ZabbixFactory):

    def make(self, macro: dict):
        return ZabbixMacro(self._zapi, macro)

    @zapi_exception("Ошибка получения Zabbix макроса")
    def get_by_filter(self, _filter: dict, **options):
        """Получение макроса из ZabbixAPI по фильтру"""
        usermacro_get = dict(
            output='extend',
            filter=_filter,
        )
        usermacro_get.update(options)
        z_macros = self._zapi.usermacro.get(**usermacro_get)
        return (self.make(m) for m in z_macros)

    def get_by_macro(self, name: str, value: str):
        return self.get_by_filter({'macro': name}, search={'value': value}, searchWildcardsEnabled=True)

    def new(self, hostid: int, macro: str, value: str = ''):
        """Создание нового макроса в ZabbixAPI"""
        return ZabbixMacro.new(self._zapi, hostid, macro, value)


class ZabbixTemplateFactory(ZabbixFactory):

    def make(self, template: dict):
        return ZabbixTemplate(self._zapi, template)

    @zapi_exception("Ошибка получения Zabbix шаблона")
    def get_by_filter(self, _filter: dict, **options):
        """Получение шаблона из ZabbixAPI по фильтру"""
        template_get = dict(
            output='extend',
            filter=_filter,
        )
        template_get.update(options)
        z_templates = self._zapi.template.get(**template_get)
        return (self.make(t) for t in z_templates)

    def get_by_name(self, template_name: str):
        """Получение шаблона из ZabbixAPI по имени"""
        return self.get_by_filter({'host': template_name})

    def get_by_group(self, group: ZabbixGroup):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        return self.get_by_filter({}, groupids=group.groupid)


class ZabbixInterfaceFactory(ZabbixFactory):

    def make(self, interface: dict):
        return ZabbixInterface(self._zapi, interface)

    @zapi_exception("Ошибка получения Zabbix узла")
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

    @zapi_exception("Ошибка получения Zabbix узла")
    def get_by_filter(self, _filter: dict, **options):
        """Получение списка объектов ZabbixHost из ZabbixAPI по фильтру"""
        host_get = dict(
            output='extend',
            filter=_filter,
        )
        host_get.update(options)
        z_hosts = self._zapi.host.get(**host_get)
        return (self.make(z_host) for z_host in z_hosts)

    def get_by_name(self, _name: str):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        return self.get_by_filter({'host': _name})

    def get_by_group(self, group: ZabbixGroup):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        hosts = self.get_by_filter({}, groupids=group.groupid)
        return hosts

    @zapi_exception("Ошибка получения Zabbix узла")
    def search(self, _search: dict, **options):
        """Поиск в ZabbixAPI"""
        host_get = dict(
            output='extend',
            search=_search,
            searchWildcardsEnabled=True,
        )
        host_get.update(options)
        z_hosts = self._zapi.host.get(**host_get)
        return (self.make(host) for host in z_hosts)

    @zapi_exception("Ошибка создания Zabbix узла")
    def new(self, host: dict):
        """Создание узла в ZabbixAPI

        :param host: Словарь Zabbix узла.
            Обязательные ключи: host, groups, interfaces
        :return: Созданный ZabbixHost объект
        :rtype: ZabbixHost
        """
        if not host.get('host') or not host.get('groups') or not host.get('interfaces'):
            raise KeyError
        z_host = dict()
        z_host['hostid'] = self._zapi.host.create(**host)['hostids'][0]
        return self.make(z_host)


class ZabbixTriggerFactory(ZabbixFactory):

    @zapi_exception("Ошибка получения Zabbix узла по триггеру")
    def _get_host_by_triggerid(self, triggerid: int):
        z_host = self._zapi.trigger.get(
            output='hosts',
            triggerids=triggerid,
            selectHosts='extend',
        )[0]['hosts'][0]
        return ZabbixHost(self._zapi, z_host)

    def make(self, trigger: dict):
        host = self._get_host_by_triggerid(int(trigger['triggerid']))
        return ZabbixTrigger(host, trigger)

    def get_by_id(self, triggerid: int):
        return ZabbixTrigger.get_by_id(self._zapi, triggerid)

    @zapi_exception("Ошибка получения Zabbix триггера")
    def get_by_filter(self, _filter: dict, **options):
        """Получение списка Zabbix триггеров из ZabbixAPI по фильтру"""
        trigger_get = dict(
            output='extend',
            filter=_filter,
        )
        trigger_get.update(options)
        z_triggers = self._zapi.trigger.get(**trigger_get)
        return (self.make(z_trigger) for z_trigger in z_triggers)


class ZabbixEventFactory(ZabbixFactory):

    @zapi_exception("Ошибка получения Zabbix триггера по событию")
    def _get_trigger_by_eventid(self, eventid: int):
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

    @zapi_exception("Ошибка получения Zabbix события")
    def get_by_groupids(self, groupids: list, limit: int = 500, **options):
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
        )
        if len(z_events) >= limit:
            return
        return (self.make(event) for event in z_events)


class ZabbixProblemFactory(ZabbixEventFactory):
    def make(self, event: dict):
        trigger = self._get_trigger_by_eventid(event['eventid'])
        return ZabbixProblem(trigger, event)

    def get_by_id(self, eventid: int):
        """Создание объекта ZabbixProblem из ZabbixAPI"""
        return ZabbixProblem.get_by_id(self._zapi, eventid)

    @zapi_exception("Ошибка получения Zabbix проблем")
    def get_by_groupids(self, groupids: List[int], limit: int = 500, **options):
        """Генератор событий из групп groupids по ZabbixAPI"""
        if groupids is None:
            groupids = [10]  # Группа по-умолчанию - A4
        time_from = int(time.time()) - (86400 * 3)  # За три последних дня
        problem_get = dict(
            output='extend',
            groupids=groupids,
            acknowledged=False,
            suppressed=False,
            time_from=time_from,
        )
        problem_get.update(options)
        z_events: list = self._zapi.problem.get(**problem_get)
        if len(z_events) >= limit:
            return
        return (self.make(event) for event in z_events)
