import logging
import re
import time
from abc import ABC
from contextlib import contextmanager

from pyzabbix import ZabbixAPI


@contextmanager
def no_index(log_message: str):
    """Менеджер контекста обработки исключения IndexError"""
    try:
        yield
    except IndexError as e:
        logging.info(log_message + str(e))


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
        return (self.make(group) for group in z_group)

    def get_by_name(self, _name: str):
        """Получение списка объекторв ZabbixGroup из ZabbixAPI по имени"""
        return self.get_by_filter({'name': _name})

    def create(self, groupname: str):
        """Создание нового узлв в ZabbixAPI

        :rtype: ZabbixGroup
        """
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
        return (self.make(m) for m in z_macros)

    def get_by_macro(self, name: str, value: str):
        return self.get_by_filter({'macro': name, 'value': value})

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
        return (self.make(t) for t in z_templates)

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
        return (self.make(z_host) for z_host in z_hosts)

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
        return (self.make(host) for host in z_hosts)

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

    def get_by_groupids(self, limit: int, groupids: list = None):
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


class Zabbix:
    """Общий класс для хранения ссылки на ZabbixAPI

    ВНИМАНИЕ!!!
    Возможно выбрасывание исключений ZabbixAPIException
    Требуется обработка прерываний"""

    def __init__(self, zapi: ZabbixAPI):
        """

        :param zapi: ссылка на объект ZabbixAPI
        """
        self._zapi = zapi


class ZabbixGroup(Zabbix):
    """Класс для работы с группами узлов Zabbix"""

    @property
    def groupid(self):
        return int(self._z_group['groupid'])

    def __init__(self, zapi: ZabbixAPI, group: dict):
        """

        :param group: группа узлов Zabbix.
            Обязательным полем является только 'groupid': id группы узлов
        :rtype: ZabbixGroup
        """
        if not group.get('groupid'):
            raise KeyError
        super().__init__(zapi)
        self._z_group = group

    @classmethod
    def get_by_id(cls, zapi: ZabbixAPI, groupid: int):
        """Создание объекта ZabbixGroup из ZabbixAPI"""
        with no_index('Zabbix group not found'):
            hostgroup_get = dict(
                output='extend',
                groupids=[groupid],
            )
            z_group = zapi.hostgroup.get(**hostgroup_get)[0]
            return cls(zapi, z_group)


class ZabbixMacro(Zabbix):
    """Класс для работы с макросами Zabbix"""

    def __init__(self, zapi: ZabbixAPI, macro: dict):
        """

        :param macro: имя макроса Zabbix.
            Обязательным полем является только 'hostmacroid': id макроса Zabbix
        :rtype: ZabbixMacro
        """
        if not macro.get('hostmacroid'):
            raise ValueError
        super().__init__(zapi)
        self._z_macro = macro

    def __str__(self):
        return self.name

    def _get(self):
        """Получение всех данных макроса из ZabbixAPI"""
        usermacro_get = dict(
            output='extend',
            hostmacroids=[self._z_macro['hostmacroid']],
        )
        with no_index('Пользовательский макрос не найдер'):
            z_macro = self._zapi.usermacro.get(**usermacro_get)[0]
            self._z_macro.update(z_macro)

    def _update(self, **kwargs):
        """Обновление данных макроса в ZabbixAPI"""
        usermacro_update = dict(
            hostmacroid=self._z_macro['hostmacroid'],
        )
        usermacro_update.update(kwargs)
        self._zapi.usermacro.update(**usermacro_update)

    @property
    def hostmacroid(self) -> int:
        return int(self._z_macro['hostmacroid'])

    @property
    def hostid(self) -> int:
        if not self._z_macro.get('hostid'):
            self._get()
        return int(self._z_macro.get('hostid'))

    @property
    def name(self) -> str:
        if not self._z_macro.get('macro'):
            self._get()
        return self._z_macro.get('macro')

    @name.setter
    def name(self, value: str):
        self._update(macro=value)

    @property
    def value(self) -> str:
        if not self._z_macro.get('value'):
            self._get()
        return self._z_macro.get('value')

    @value.setter
    def value(self, value: str):
        self._update(value=value)


class ZabbixTemplate(Zabbix):
    """Класс для работы с шаблонами Zabbix"""

    def __init__(self, zapi: ZabbixAPI, template: dict):
        """

        :param template: Шаблон Zabbix.
            Обязательным полем является только 'templateid'
        :rtype: ZabbixTemplate
        """
        if not template.get('templateid'):
            raise KeyError
        super().__init__(zapi)
        self.z_template = template

    def _get(self):
        """Получение всех данных шаблона"""
        template_get = dict(
            output='extend',
            templateids=self.z_template.get('templateid'),
        )
        z_template = self._zapi.template.get(**template_get)[0]
        self.z_template.update(z_template)

    @property
    def host(self) -> str:
        if not self.z_template.get('host'):
            self._get()
        return self.z_template.get('host')

    @property
    def name(self) -> str:
        if not self.z_template.get('name'):
            self._get()
        return self.z_template.get('name')

    @property
    def description(self) -> str:
        if not self.z_template.get('description'):
            self._get()
        return self.z_template.get('description')


class ZabbixInterface(Zabbix):
    """Класс для работы с интерфейсами узлов Zabbix"""

    def __init__(self, zapi: ZabbixAPI, interface: dict):
        """

        :param interface: интерфейс узла Zabbix.
            Обязательным полем является только 'interfaceid': id интерфейса узла Zabbix
        :rtype: ZabbixInterface
        """
        if not interface.get('interfaceid'):
            raise KeyError
        super().__init__(zapi)
        self._z_interface = interface

    def _get(self, **kwargs):
        """Получение всех данных интерфейса из ZabbixAPI"""
        interface_get = dict(
            output='extend',
            interfaceid=self._z_interface.get('interfaceid')
        )
        interface_get.update(kwargs)
        z_interface = self._zapi.hostinterface.get(**interface_get)[0]
        self._z_interface.update(z_interface)

    def _update(self, **kwargs):
        """Обновление данных узла в ZabbixAPI"""
        interface_update = dict(
            interfaceid=self._z_interface.get('interfaceid'),
        )
        interface_update.update(kwargs)
        self._zapi.hostinterface.update(**interface_update)

    @property
    def interfaceid(self) -> int:
        return int(self._z_interface.get('interfaceid'))

    @property
    def dns(self) -> str:
        if not self._z_interface.get('dns'):
            self._get()
        return self._z_interface.get('dns')

    @dns.setter
    def dns(self, value):
        self._update(dns=value)
        self._z_interface['dns'] = value

    @property
    def hostid(self) -> int:
        if not self._z_interface.get('hostid'):
            self._get()
        return int(self._z_interface.get('hostid'))

    @property
    def ip(self) -> str:
        if not self._z_interface.get('ip'):
            self._get()
        return self._z_interface.get('ip')

    @ip.setter
    def ip(self, value):
        self._update(ip=value)
        self._z_interface['ip'] = value

    @property
    def main(self) -> int:
        if not self._z_interface.get('main'):
            self._get()
        return int(self._z_interface.get('main'))

    @property
    def port(self) -> int:
        if not self._z_interface.get('port'):
            self._get()
        return int(self._z_interface.get('port'))

    @property
    def type(self) -> int:
        """Тип интерфейса

        Возможные значения:
        1 - агент;
        2 - SNMP;
        3 - IPMI;
        4 - JMX.
        """
        if not self._z_interface.get('type'):
            self._get()
        return int(self._z_interface.get('type'))

    @property
    def useip(self) -> int:
        if not self._z_interface.get('useip'):
            self._get()
        return int(self._z_interface.get('useip'))

    @useip.setter
    def useip(self, value: int):
        """0 - use ip, 1 - use DNS"""
        self._update(useip=value)
        self._z_interface['useip'] = value


class ZabbixHost(Zabbix):
    """Класс для работы с узлами Zabbix"""

    def _get(self, **kwargs):
        """Получение всех данных узла из ZabbixAPI"""
        host_get = dict(
            output='extend',
            hostids=self._z_host['hostid'],
        )
        host_get.update(kwargs)
        with no_index('Узел не найден'):
            z_host = self._zapi.host.get(**host_get)[0]
            self._z_host.update(z_host)

    def _update(self, **kwargs):
        """Обновление данных узла в ZabbixAPI"""
        host_update = dict(
            hostid=self._z_host['hostid'],
        )
        host_update.update(kwargs)
        self._zapi.host.update(**host_update)

    @property
    def hostid(self) -> int:
        return int(self._z_host['hostid'])

    @property
    def host(self) -> str:
        if self._z_host.get('host') is None:
            self._get()
        return self._z_host.get('host')

    @host.setter
    def host(self, value: str):
        self._update(host=value)
        self._z_host['host'] = value

    @property
    def name(self) -> str:
        if self._z_host.get('name') is None:
            self._get()
        return self._z_host.get('name')

    @name.setter
    def name(self, value: str):
        self._update(name=value)
        self._z_host['name'] = value

    @property
    def is_vip(self) -> str:
        if not self._vip:
            self._vip = self._get_VIP()
        return self._vip

    def __init__(self, zapi: ZabbixAPI, host: dict):
        """

        :param host: Узел Zabbix.
            Обязательным полем host является только 'hostid': id узла Zabbix
        :rtype: ZabbixHost
        """
        if not host.get('hostid'):
            raise ValueError
        super().__init__(zapi)
        self._z_host = host
        self._macros = list()  # список ZabbixMacro
        self._interfaces = list()  # список ZabbixInterface
        self._parent_templates = list()  # список ZabbixTemplate
        self._vip = None

    def __str__(self) -> str:
        return self.host

    @classmethod
    def get_by_id(cls, zapi: ZabbixAPI, hostid: int):
        """Создание объекта ZabbixHost из ZabbixAPI"""
        z_host = zapi.host.get(
            output='extend',
            hostids=[hostid],
        )
        return cls(zapi, z_host)

    def _get_VIP(self) -> str:
        """Получение статуса коммутатора"""
        is_svip = self.get_macro(r'{$IS_SVIP}').value
        is_vip = self.get_macro(r'{$IS_VIP}').value
        if is_svip and int(is_svip) == 1:
            return 'SVIP'
        elif is_vip and int(is_vip) == 1:
            return 'VIP'
        return ''

    @property
    def status(self) -> int:
        return int(self._z_host.get('status'))

    @status.setter
    def status(self, value: int):
        self._update(status=value)
        self._z_host['status'] = value

    def is_monitored(self) -> bool:
        if self._z_host.get('status') is None:
            self._get()
        return self._z_host.get('status') == 0

    @property
    def macros(self):
        if not self._macros:
            if not self._z_host.get('macros'):
                self._get(output='macros', selectMacros='extend')
            self._macros = [ZabbixMacro(self._zapi, m) for m in self._z_host.get('macros')]
        return self._macros

    def get_macro(self, macro: str):
        """Получение пользовательского макроса (объект типа ZabbixMacro)

        :rtype: ZabbixMacro
        """
        return list(filter(lambda m: m.name == macro, self.macros))[0]

    @property
    def parent_templates(self):
        """Возвращает список привязанных шаблонов

        :rtype: list[ZabbixTemplate]
        """
        # Если список пуст или не равен списку _z_host['parentTemplates']
        if not self._parent_templates or len(self._parent_templates) != len(self._z_host.get('parentTemplates')):
            if not self._z_host.get('parentTemplates'):
                self._get(output='parentTemplates', selectParentTemplates='extend')
            self._parent_templates = [ZabbixTemplate(self._zapi, t) for t in self._z_host.get('parentTemplates')]
        return self._parent_templates

    def link_template(self, template: ZabbixTemplate):
        """Привязывает новый шаблон"""
        self._z_host['parentTemplates'].append(template.z_template)
        z_parent_templateids = [{'templateid': t.templateid} for t in self._z_host.get('parentTemplates')]
        self._update(templates=z_parent_templateids)
        self._parent_templates.append(template)

    def find_parent_templates(self, template_name: str):
        """Поиск шаблонов, начинающихся на указанный текст

        :rtype: list[ZabbixTemplate]
        """
        return list(filter(lambda t: re.match(template_name, t.host), self.parent_templates))

    @property
    def interfaces(self):
        if not self._interfaces or len(self._interfaces) != len(self._z_host.get('interfaces')):
            if not self._z_host.get('interfaces'):
                self._get(output='interfaces', selectInterfaces='extend')
            self._interfaces = [ZabbixInterface(self._zapi, i) for i in self._z_host.get('interfaces')]
        return self._interfaces

    def get_main_interface(self):
        main_interface = next(filter(lambda i: int(i.main) == 1, self.interfaces))
        return main_interface

    def get_ip(self):
        """Получение ip основного интерфейса"""
        return self.get_main_interface().ip

    @property
    def inventory(self) -> dict:
        if not self._z_host.get('inventory'):
            self._get(output='inventory', selectInventory='extend')
        return self._z_host.get('inventory')

    @inventory.setter
    def inventory(self, value: dict):
        self._update(inventory=value)


class ZabbixTrigger(Zabbix):
    """Класс для работы с узлами Zabbix"""

    def is_trigger_A4(self):
        """Триггер по недоступности A4?"""
        return re.match(r'^A4-[0-9]{5}-', str(self._host)) and re.search(r'Коммутатор недоступен',
                                                                         self.description)

    def is_trigger_E4(self):
        """Триггер по недоступности E4?"""
        return re.match(r'^E4-', str(self._host))

    def is_trigger_Enforta(self):
        """Триггер по недоступности Enforta-A4?"""
        return re.match(r'^En4', str(self._host.name))

    def is_trigger_lorawan(self):
        """Триггер по недоступности lorawan?"""
        return re.match(r'^NSK-IBS-', str(self._host))

    def is_trigger_battery(self):
        """Триггер по работе от батареи A4?"""
        return re.match(r'^A4-[0-9]{5}-', str(self._host)) and re.search(r'работает от батареи', self.description)

    def is_trigger_K4(self):
        """Триггер по недоступности A4?"""
        return re.match(r'^K4-', self._host.name) and re.search(r'Коммутатор недоступен', self.description)

    def is_trigger_A4TV(self):
        """Триггер по недоступности K4MM?"""
        return re.match(r'^K4MM-', str(self._host)) and re.search(r'не пингуется', self.description)

    def is_trigger_A4TV_optic(self):
        """Триггер по отсутствию оптического сигнала K4MM?"""
        return re.match(r'^K4MM-', str(self._host)) and re.search(r'^Нет опт.сигнала', self.description)

    def is_trigger_A4TV_optic_low(self):
        """Триггер по слабому оптическому сигнала K4MM?"""
        return re.match(r'^K4MM-', str(self._host)) and re.search(r'^Слабый опт.сигнал', self.description)

    def is_trigger_magistr_error(self):
        """Триггер по ошибкам на магистратьном порту?"""
        return re.search(r'Растут ошибки на магистральном порту', self.description)

    def is_trigger_stp(self):
        """Триггер по разрывам STP?"""
        return re.search(r'Разрыв STP кольца', self.description)

    def __init__(self, host: ZabbixHost, trigger: dict):
        """

        :param trigger: Триггер Zabbix.
            Обязательное поле 'triggerid'
        :rtype: ZabbixTrigger
        """
        if not trigger.get('triggerid'):
            raise KeyError
        super().__init__(host._zapi)
        self._z_trigger = trigger
        self._host: ZabbixHost = host

    def _get(self, **kwargs):
        """Получение всех данных триггера из ZabbixAPI"""
        trigger_get = dict(
            output='extend',
            triggerids=self._z_trigger['triggerid'],
        )
        trigger_get.update(kwargs)
        with no_index('Триггер не найден'):
            z_trigger = self._zapi.trigger.get(**trigger_get)[0]
            self._z_trigger.update(z_trigger)

    @classmethod
    def get_by_id(cls, zapi: ZabbixAPI, triggerid: int):
        trigger_get = dict(
            output='extend',
            triggerids=[triggerid],
            expandExpression='true',
            expandDescription='true',
            expandData='true',
            selectHosts='extend',
        )
        with no_index('Триггер не найден'):
            z_trigger = zapi.trigger.get(**trigger_get)[0]
            return cls(ZabbixHost(zapi, z_trigger['hosts'][0]), z_trigger)

    @property
    def triggerid(self) -> int:
        return int(self._z_trigger['triggerid'])

    @property
    def value(self) -> int:
        if not self._z_trigger.get('value'):
            self._get()
        return int(self._z_trigger.get('value'))

    @property
    def host(self) -> ZabbixHost:
        if self._z_trigger.get('host') is None:
            self._get()
        return self._host

    @property
    def description(self) -> str:
        if not self._z_trigger.get('description'):
            self._get()
        return self._z_trigger.get('description')

    def _get_last_events(self, since=None, limit=10, acknowledged=None, value=None):
        """Получение последних событий из Zabbix API по триггеру"""
        if since is None:
            since = int(time.time()) - (3600 * 1)
        event_get = dict(
            output=['clock', 'eventid', 'value', 'acknowledged', 'extend'],
            objectids=self._z_trigger['triggerid'],
            sortfield=['clock', 'eventid'],
            sortorder='DESC',  # сортировка от более нового к более старому
            limit=limit,
            time_from=since,
            select_acknowledges=['acknowledgeid', 'clock', 'message'],
            filter={'acknowledges': {'message': '-'}},
        )
        if acknowledged is not None:
            event_get.update({
                'acknowledged': acknowledged,
            })
        if value is not None:
            event_get.update({
                'value': value
            })
        z_event = self._zapi.event.get(**event_get)
        return z_event

    def get_last_events(self):
        """Получение последних событий из ZabbixAPI для этого триггера """
        z_events = self._get_last_events()
        return (ZabbixEvent.get_by_id(self._zapi, e.get('eventid')) for e in z_events)

    def get_last_tickets_keys(self):
        """Получение последних сообщений подтверждённых событий по триггеру из Zabbix API"""
        z_events = self._get_last_events(acknowledged='True', value=1)
        # Получаем список ключей тикетов
        return (e.get('message') for e in z_events)


class ZabbixEvent(Zabbix):
    """Класс для работы с событиями Zabbix"""

    def __init__(self, trigger: ZabbixTrigger, event: dict):
        """

        :param trigger: Триггер, по которому создалось событие.
        :param event: Событие Zabbix.
            Обязательным полем является только 'eventid'
        :rtype: ZabbixEvent
        """
        if not event.get('eventid'):
            raise KeyError
        super().__init__(trigger._zapi)
        self._trigger = trigger
        self._z_event = event

    def _get(self, **kwargs):
        """Получение всех данных узла из ZabbixAPI"""
        event_get = dict(
            output='extend',
            eventids=self._z_event['eventid'],
        )
        event_get.update(kwargs)
        with no_index('Событие не найдено'):
            z_event = self._trigger.host._zapi.event.get(**event_get)[0]
            self._z_event.update(z_event)

    @classmethod
    def get_by_id(cls, zapi: ZabbixAPI, eventid: int):
        """Создание объекта ZabbixEvent из ZabbixAPI"""
        event_get = dict(
            output='extend',
            eventids=[eventid],
        )
        with no_index('Событие не создано'):
            z_event = zapi.event.get(**event_get)[0]
            trigger = ZabbixTrigger.get_by_id(zapi, z_event['objectid'])
            if trigger:
                return cls(trigger, z_event)

    @property
    def eventid(self) -> int:
        return int(self._z_event['eventid'])

    @property
    def clock(self) -> int:
        if not self._z_event.get('clock'):
            self._get()
        return int(self._z_event.get('clock'))

    @property
    def trigger(self) -> ZabbixTrigger:
        return self._trigger

    @property
    def acknowledged(self):
        if not self._z_event.get('acknowledged'):
            self._get()
        return int(self._z_event.get('acknowledged'))

    def ack(self, message, action=6):
        """Подтверждаем в Zabbix

        Возможные значения *action*:
            * 1 - закрыть проблемы
            * 2 - подтвердить событие
            * 4 - добавить сообщение
            * 8 - изменить важность
        :param str message: Текст сообщения
        :param int action: Сумма действий (например 7=1+2+4)
        """
        event_ack = dict(
            eventids=self._z_event['eventid'],
            action=action,  # 2 - подтвердить событие, 4 - добавить сообщение
            message=message
        )
        self._zapi.event.acknowledge(**event_ack)
        self._z_event['acknowledged'] = 1
