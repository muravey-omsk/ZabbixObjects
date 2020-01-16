from abc import ABC
from typing import Union, Generator

from .Zabbix import *


class ZabbixFactory(Zabbix, ABC):
    pass


class ZabbixProxyFactory(ZabbixFactory):

    def __make(self, proxy: dict):
        return ZabbixProxy(self._zapi, proxy)

    @zapi_exception("Ошибка получения Zabbix прокси")
    def __get(self, **options) -> list:
        return self._zapi.proxy.get(**options)

    def get_by_filter(self, _filter: dict, **options) -> Generator[ZabbixProxy, None, None]:
        """Получение списка объектов ZabbixGroup из ZabbixAPI по фильтру"""
        z_proxies: list = self.__get(filter=_filter, **options)
        return (self.__make(proxy) for proxy in z_proxies)

    def get_by_host(self, _name: Union[str, List[str]]):
        """Получение списка объекторв ZabbixProxy из ZabbixAPI по имени"""
        z_hosts = self.get_by_filter({'host': _name})
        return z_hosts


class ZabbixGroupFactory(ZabbixFactory):

    def __make(self, group: dict):
        return ZabbixGroup(self._zapi, group)

    @zapi_exception("Ошибка получения Zabbix группы", logging.CRITICAL)
    def __get(self, **options) -> list:
        return self._zapi.hostgroup.get(**options)

    def get_by_id(self, groupid: int):
        """Создание объекта ZabbixGroup из ZabbixAPI"""
        z_group = self.__get(groupids=[groupid])[0]
        return self.__make(z_group)

    def get_by_filter(self, _filter: dict) -> Generator[ZabbixGroup, None, None]:
        """Получение списка объектов ZabbixGroup из ZabbixAPI по фильтру"""
        z_groups = self.__get(filter=_filter)
        return (self.__make(group) for group in z_groups)

    def get_by_name(self, _name: Union[str, List[str]]):
        """Получение списка объекторв ZabbixGroup из ZabbixAPI по имени"""
        return self.get_by_filter({'name': _name})

    @zapi_exception("Ошибка создания Zabbix группы")
    def create(self, groupname: str):
        """Создание нового узлв в ZabbixAPI"""
        z_groups = self._zapi.hostgroup.create(name=groupname)
        return self.__make({'groupid': z_groups.get('groupids')[0]})


class ZabbixMacroFactory(ZabbixFactory):

    def __make(self, macro: dict):
        return ZabbixMacro(self._zapi, macro)

    @zapi_exception("Ошибка получения Zabbix макроса")
    def __get(self, **options) -> list:
        return self._zapi.usermacro.get(**options)

    def get_by_filter(self, _filter: dict, **options):
        """Получение макроса из ZabbixAPI по фильтру"""
        z_macros = self.__get(filter=_filter, **options)
        return (self.__make(m) for m in z_macros)

    def get_by_macro(self, name: str, value: str):
        return self.get_by_filter({'macro': name}, search={'value': value}, searchWildcardsEnabled=True)

    def create(self, hostid: int, macro: str, value: str = ''):
        """Создание нового макроса в ZabbixAPI"""
        return ZabbixMacro.create(self._zapi, hostid, macro, value)


class ZabbixTemplateFactory(ZabbixFactory):

    def __make(self, template: dict):
        return ZabbixTemplate(self._zapi, template)

    @zapi_exception("Ошибка получения Zabbix шаблона")
    def __get(self, **options) -> list:
        return self._zapi.template.get(**options)

    def get_by_filter(self, _filter: dict, **options):
        """Получение шаблона из ZabbixAPI по фильтру"""
        z_templates = self.__get(filter=_filter, **options)
        return (self.__make(t) for t in z_templates)

    def get_by_name(self, template_name: str):
        """Получение шаблона из ZabbixAPI по имени"""
        return self.get_by_filter({'host': template_name})

    def get_by_group(self, group: ZabbixGroup):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        return self.__get(groupids=group.groupid)


class ZabbixInterfaceFactory(ZabbixFactory):

    def __make(self, interface: dict):
        return ZabbixInterface(self._zapi, interface)

    @zapi_exception("Ошибка получения Zabbix узла")
    def __get(self, **options) -> list:
        return self._zapi.hostinterface.get(**options)

    def get_by_id(self, interfaceid: int):
        """Создание объекта ZabbixInterface из ZabbixAPI"""
        z_interface = self.__get(interfaceid=interfaceid)[0]
        return self.__make(z_interface)


class ZabbixHostFactory(ZabbixFactory):

    def __make(self, host: dict):
        return ZabbixHost(self._zapi, host)

    @zapi_exception("Ошибка получения Zabbix узла")
    def __get(self, **options) -> list:
        return self._zapi.host.get(**options)

    def get_by_id(self, hostid: int):
        """Создание объекта ZabbixHost из ZabbixAPI"""
        z_host = self.__get(hostids=hostid)[0]
        return self.__make(z_host)

    def get_by_filter(self, _filter: dict, **options):
        """Получение списка объектов ZabbixHost из ZabbixAPI по фильтру"""
        z_hosts = self.__get(filter=_filter, **options)
        return (self.__make(z_host) for z_host in z_hosts)

    def get_by_name(self, _name: str):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        return self.get_by_filter({'host': _name})

    def get_by_group(self, group: ZabbixGroup):
        """Получение списка узлов ZabbixHost из ZabbixAPI по видимому имени"""
        hosts = self.__get(groupids=group.groupid)
        return (self.__make(host) for host in hosts)

    def search(self, _search: dict, **options):
        """Поиск в ZabbixAPI"""
        z_hosts = self.__get(search=_search, searchWildcardsEnabled=True, **options)
        return (self.__make(host) for host in z_hosts)

    @zapi_exception("Ошибка создания Zabbix узла")
    def create(self, host: dict):
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
        return self.__make(z_host)


class ZabbixTriggerFactory(ZabbixFactory):

    def __make(self, trigger: dict):
        host = self._get_host_by_triggerid(int(trigger['triggerid']))
        return ZabbixTrigger(host, trigger)

    @zapi_exception("Ошибка получения Zabbix узла по триггеру")
    def __get(self, **options) -> list:
        return self._zapi.trigger.get(**options)

    def _get_host_by_triggerid(self, triggerid: int):
        z_host = self.__get(
            triggerids=triggerid,
            selectHosts='extend',
        )[0]['hosts'][0]
        return ZabbixHost(self._zapi, z_host)

    def get_by_id(self, triggerid: int):
        z_trigger = self.__get(
            triggerids=[triggerid],
            expandExpression='true',
            expandDescription='true',
            expandData='true',
            selectHosts='extend',
        )[0]
        return self.__make(z_trigger)

    def get_by_filter(self, _filter: dict, **options):
        """Получение списка Zabbix триггеров из ZabbixAPI по фильтру"""
        z_triggers = self.__get(filter=_filter, **options)
        return (self.__make(z_trigger) for z_trigger in z_triggers)


class ZabbixEventFactory(ZabbixFactory):

    def __make(self, event: dict):
        trigger = self._get_trigger_by_eventid(event['eventid'])
        return ZabbixEvent(trigger, event)

    @zapi_exception("Ошибка получения Zabbix триггера по событию")
    def __get(self, **options) -> list:
        return self._zapi.event.get(**options)

    def _get_trigger_by_eventid(self, eventid: int):
        z_event = self.__get(
            output=['relatedObject', 'hosts'],
            eventids=eventid,
            selectRelatedObject='extend',
            selectHosts='extend',
        )[0]
        z_trigger = z_event['relatedObject']
        z_host = z_event['hosts'][0]
        host = ZabbixHost(self._zapi, z_host)
        return ZabbixTrigger(host, z_trigger)

    def get_by_id(self, eventid: int):
        """Создание объекта ZabbixEvent из ZabbixAPI"""
        z_event = self.__get(eventids=[eventid])[0]
        return self.__make(z_event)

    def get_by_trigger(self, trigger: ZabbixTrigger, limit=100, **options):
        event_get = dict(
            objectids=trigger.triggerid,
            sortfield=['clock', 'eventid'],
            sortorder='DESC',  # сортировка от более нового к более старому
            limit=limit,
            select_acknowledges=['acknowledgeid', 'clock', 'message'],
        )
        event_get.update(options)
        z_events = self.__get(**event_get)
        return (self.__make(event) for event in z_events)


class ZabbixProblemFactory(ZabbixEventFactory):

    def __make(self, event: dict):
        trigger = self._get_trigger_by_eventid(event['eventid'])
        return ZabbixProblem(trigger, event)

    @zapi_exception("Ошибка получения Zabbix проблем")
    def __get(self, **options) -> list:
        return self._zapi.problem.get(**options)

    def get_by_id(self, eventid: int, recent=False):
        z_problems = self.__get(eventid=eventid, recent=recent)
        return (self.__make(problem) for problem in z_problems)

    def get_by_tag(self, tag: str, limit: int = 500, **options):
        z_events = self.__get(
            time_from=int(time.time()) - (3 * 86400),
            tags=[{'tag': tag}],
            acknowledged=False,
            suppressed=False,
            **options,
        )
        if z_events is None or len(z_events) >= limit:
            return
        return (self.__make(event) for event in z_events)

    def get_by_groupids(self, groupids: List[int], limit: int = 500, **options):
        """Генератор событий из групп groupids по ZabbixAPI"""
        if groupids is None:
            groupids = [10]  # Группа по-умолчанию - A4
        time_from = int(time.time()) - (86400 * 3)  # За три последних дня
        z_problems = self.__get(
            groupids=groupids,
            acknowledged=False,
            suppressed=False,
            time_from=time_from,
            **options,
        )
        if len(z_problems) >= limit:
            return
        return (self.__make(problem) for problem in z_problems)
