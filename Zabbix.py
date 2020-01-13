import logging
import re
import time
from typing import List

from pyzabbix import ZabbixAPI, ZabbixAPIException

log = logging.getLogger(__name__)


def strftime(seconds: int, strformat="%d/%b/%Y %H:%M"):
    """Форматирование времени из unixtime"""
    return time.strftime(strformat, time.localtime(int(seconds)))


def zapi_exception(log_message: str, level=logging.ERROR):
    """Создание декоратора с заданным сообщение в лог"""

    def decorator(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ZabbixAPIException as ze:
                log.error("%s: %s: %s", log_message, ze.message, ze.data)

        return wrapper

    def critical_decorator(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ZabbixAPIException as ze:
                log.critical("%s: %s: %s", log_message, ze.message, ze.data)

        return wrapper

    if level == logging.ERROR:
        return decorator
    elif level == logging.CRITICAL:
        return critical_decorator


class Zabbix:
    """Общий класс для хранения ссылки на ZabbixAPI"""

    def __init__(self, zapi: ZabbixAPI):
        """

        :param zapi: ссылка на объект ZabbixAPI
        """
        self._zapi = zapi
        self._z_dict = None

    @property
    def dict(self) -> dict:
        return {'zabbix': self._z_dict}


class ZabbixConfiguration(Zabbix):

    @zapi_exception("Ошибка экпорта")
    def do_export(self, _options: dict, _format='json'):
        """
        https://www.zabbix.com/documentation/4.2/ru/manual/api/reference/configuration/export

        Объект `options` имеет следующие параметры::
            `groups` - (массив) ID экспортируемых групп узлов сети;
            `hosts` - (массив) ID экспортируемых узлов сети;
            `images` - (массив) ID экспортируемых изображений;
            `maps` - (массив) ID экспортируемых карт сетей;
            `screens` - (массив) ID экспортируемых комплексных экранов;
            `templates` - (массив) ID экспортируемых шаблонов;
            `valueMaps` - (массив) ID экспортируемых преобразований значений.
        "params": {
            "options": {
                "hosts": [ "10161" ]
            },
            "format": "xml"
        }

        :param _options: Экспортируемые объекты
        :param _format: Формат, в котором необходимо экспортировать данные.
            Возможные значения: json, xml.
        """
        configuration_export = dict(
            options=_options,
            format=_format,
        )
        result = self._zapi.configuration.export(**configuration_export)
        return result

    @zapi_exception("Ошибка импорта")
    def do_import(self, _source: str, _rules: dict, _format='json'):
        """

        https://www.zabbix.com/documentation/4.2/ru/manual/api/reference/configuration/import

        "params": {
            "format": "json",
            "rules": {
                "applications": {
                    "createMissing": true,
                    "deleteMissing": false
                },
                "valueMaps": {
                    "createMissing": true,
                    "updateExisting": false
                },
                "hosts": {
                    "createMissing": true,
                    "updateExisting": true
                },
                "items": {
                    "createMissing": true,
                    "updateExisting": true,
                    "deleteMissing": true
                }
            },
        }

        :param _source: Сериализованная строка, которая содержит данные конфигурации.
        :param _rules: Правила, каким образом необходимо импортировать новые и существующие объекты.
        :param _format: Формат сериализованной строки: json, xml.

        """
        configuration_import = dict(
            source=_source,
            rules=_rules,
            format=_format,
        )
        # noinspection PyTypeChecker
        result = self._zapi.do_request('configuration.import', configuration_import)
        return result


class ZabbixProxy(Zabbix):

    def __init__(self, zapi: ZabbixAPI, proxy: dict):
        if not proxy.get('proxyid'):
            raise KeyError
        super().__init__(zapi)
        self._z_dict = proxy

    def __str__(self):
        return self.host

    @zapi_exception("Ошибка получения данных Zabbix прокси")
    def __get(self, **options):
        proxy_get = dict(
            output='extend',
            proxyids=self._z_dict['proxyid'],
        )
        proxy_get.update(options)
        z_proxy = self._zapi.proxy.get(proxy_get)[0]
        self._z_dict.update(z_proxy)

    @property
    def proxyid(self):
        return self._z_dict.get('proxyid')

    @property
    def host(self) -> str:
        if not self._z_dict.get('host'):
            self.__get()
        return self._z_dict.get('host')

    @property
    def status(self) -> int:
        if not self._z_dict.get('status'):
            self.__get()
        return int(self._z_dict.get('status'))


class ZabbixGroup(Zabbix):
    """Класс для работы с группами узлов Zabbix"""

    def __init__(self, zapi: ZabbixAPI, group: dict):
        """

        :param group: группа узлов Zabbix.
            Обязательным полем является только 'groupid': id группы узлов
        :rtype: ZabbixGroup
        """
        if not group.get('groupid'):
            raise KeyError
        super().__init__(zapi)
        self._z_dict = group

    def __str__(self) -> str:
        return self._z_dict.get('name')

    @zapi_exception("Ошибка получения данных Zabbix группы")
    def __get(self, **options):
        hostgroup_get = dict(
            output='extend',
            groupids=self._z_dict['groupid'],
        )
        hostgroup_get.update(options)
        z_group = self._zapi.hostgroup.get(**hostgroup_get)[0]
        self._z_dict.update(z_group)

    @property
    def groupid(self):
        return int(self._z_dict['groupid'])

    @property
    def name(self):
        if not self._z_dict.get('name'):
            self.__get()
        return self._z_dict.get('name')


class ZabbixMacro(Zabbix):
    """Класс для работы с макросами Zabbix"""

    def __init__(self, zapi: ZabbixAPI, macro: dict):
        """

        :param macro: имя макроса Zabbix.
            Обязательным полем является только 'hostmacroid': id макроса Zabbix
        :rtype: ZabbixMacro
        """
        if not macro.get('hostmacroid'):
            raise KeyError
        super().__init__(zapi)
        self._z_dict = macro

    def __str__(self):
        return self.name

    @zapi_exception("Ошибка получения данных Zabbix макроса")
    def __get(self):
        """Получение всех данных макроса из ZabbixAPI"""
        usermacro_get = dict(
            output='extend',
            hostmacroids=[self._z_dict['hostmacroid']],
        )
        z_macro = self._zapi.usermacro.get(**usermacro_get)[0]
        self._z_dict.update(z_macro)

    @zapi_exception("Ошибка обновления данных Zabbix макроса")
    def __update(self, **kwargs):
        """Обновление данных макроса в ZabbixAPI"""
        usermacro_update = dict(
            hostmacroid=self._z_dict['hostmacroid'],
        )
        usermacro_update.update(kwargs)
        self._zapi.usermacro.update(**usermacro_update)

    @property
    def hostmacroid(self) -> int:
        return int(self._z_dict['hostmacroid'])

    @property
    def hostid(self) -> int:
        if not self._z_dict.get('hostid'):
            self.__get()
        return int(self._z_dict.get('hostid'))

    @property
    def name(self) -> str:
        if not self._z_dict.get('macro'):
            self.__get()
        return self._z_dict.get('macro')

    @name.setter
    def name(self, value: str):
        self.__update(macro=value)
        self._z_dict['macro'] = value

    @property
    def value(self) -> str:
        if not self._z_dict.get('value'):
            self.__get()
        return self._z_dict.get('value')

    @value.setter
    def value(self, value: str):
        self.__update(value=value)
        self._z_dict['value'] = value

    @classmethod
    @zapi_exception("Ошибка создания Zabbix макроса")
    def create(cls, zapi: ZabbixAPI, hostid: int, macro: str, value: str):
        """Создание нового макроса в ZabbixAPI"""
        usermacro_create = dict(
            hostid=hostid,
            macro=macro,
            value=value,
        )
        z_hostmacroid = zapi.usermacro.create(**usermacro_create)['hostmacroids'][0]
        return cls(zapi, dict(hostmacroid=z_hostmacroid))


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
        self._z_dict = template

    def __str__(self) -> str:
        return self.name

    @zapi_exception("Ошибка получения данных Zabbix макроса")
    def __get(self):
        """Получение всех данных шаблона"""
        template_get = dict(
            output='extend',
            templateids=self._z_dict.get('templateid'),
        )
        z_template = self._zapi.template.get(**template_get)[0]
        self._z_dict.update(z_template)

    @property
    def templateid(self):
        return self._z_dict['templateid']

    @property
    def host(self) -> str:
        if not self._z_dict.get('host'):
            self.__get()
        return self._z_dict.get('host')

    @property
    def name(self) -> str:
        if not self._z_dict.get('name'):
            self.__get()
        return self._z_dict.get('name')

    @property
    def description(self) -> str:
        if not self._z_dict.get('description'):
            self.__get()
        return self._z_dict.get('description')


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
        self._z_dict = interface

    @zapi_exception("Ошибка получения данных Zabbix интерфейса")
    def __get(self, **kwargs):
        """Получение всех данных интерфейса из ZabbixAPI"""
        interface_get = dict(
            output='extend',
            interfaceid=self._z_dict.get('interfaceid')
        )
        interface_get.update(kwargs)
        z_interface = self._zapi.hostinterface.get(**interface_get)[0]
        self._z_dict.update(z_interface)

    @zapi_exception("Ошибка обновления данных Zabbix интерфейса")
    def __update(self, **kwargs):
        """Обновление данных узла в ZabbixAPI"""
        interface_update = dict(
            interfaceid=self._z_dict.get('interfaceid'),
        )
        interface_update.update(kwargs)
        self._zapi.hostinterface.update(**interface_update)

    @property
    def interfaceid(self) -> int:
        return int(self._z_dict.get('interfaceid'))

    @property
    def dns(self) -> str:
        if not self._z_dict.get('dns'):
            self.__get()
        return self._z_dict.get('dns')

    @dns.setter
    def dns(self, value):
        self.__update(dns=value)
        self._z_dict['dns'] = value

    @property
    def hostid(self) -> int:
        if not self._z_dict.get('hostid'):
            self.__get()
        return int(self._z_dict.get('hostid'))

    @property
    def ip(self) -> str:
        if not self._z_dict.get('ip'):
            self.__get()
        return self._z_dict.get('ip')

    @ip.setter
    def ip(self, value: str):
        self.__update(ip=value)
        self._z_dict['ip'] = value

    @property
    def main(self) -> int:
        if not self._z_dict.get('main'):
            self.__get()
        return int(self._z_dict.get('main'))

    @property
    def port(self) -> int:
        if not self._z_dict.get('port'):
            self.__get()
        return int(self._z_dict.get('port'))

    @property
    def type(self) -> int:
        """Тип интерфейса

        Возможные значения:
        1 - агент;
        2 - SNMP;
        3 - IPMI;
        4 - JMX.
        """
        if not self._z_dict.get('type'):
            self.__get()
        return int(self._z_dict.get('type'))

    @property
    def useip(self) -> int:
        if not self._z_dict.get('useip'):
            self.__get()
        return int(self._z_dict.get('useip'))

    @useip.setter
    def useip(self, value: int):
        """0 - use ip, 1 - use DNS"""
        self.__update(useip=value)
        self._z_dict['useip'] = value


class ZabbixHost(Zabbix):
    """Класс для работы с узлами Zabbix"""

    def __init__(self, zapi: ZabbixAPI, host: dict):
        """

        :param host: Узел Zabbix.
            Обязательным полем host является только 'hostid': id узла Zabbix
        :rtype: ZabbixHost
        """
        if not host.get('hostid'):
            raise KeyError
        super().__init__(zapi)
        self._z_dict = host
        self._macros = list()  # список ZabbixMacro
        self._interfaces = list()  # список ZabbixInterface
        self._vip = None
        self._groups = None

    def __str__(self) -> str:
        return self.host

    @zapi_exception("Ошибка получения данных Zabbix узла")
    def __get(self, **options):
        """Получение всех данных узла из ZabbixAPI"""
        host_get = dict(
            output='extend',
            hostids=self._z_dict['hostid'],
        )
        host_get.update(options)
        z_host = self._zapi.host.get(**host_get)[0]
        self._z_dict.update(z_host)

    @zapi_exception("Ошибка обновления данных Zabbix узла")
    def __update(self, **options):
        """Обновление данных узла в ZabbixAPI"""
        host_update = dict(
            hostid=self._z_dict['hostid'],
        )
        host_update.update(options)
        self._zapi.host.update(**host_update)

    @property
    def hostid(self) -> int:
        return int(self._z_dict['hostid'])

    @property
    def host(self) -> str:
        if self._z_dict.get('host') is None:
            self.__get()
        return self._z_dict.get('host')

    @host.setter
    def host(self, value: str):
        try:
            self.__update(host=value)
            self._z_dict['host'] = value
        except ZabbixAPIException as e:
            log.error("Ошибка переименовывания: %s", e.data, extra=self.dict)

    @property
    def name(self) -> str:
        if self._z_dict.get('name') is None:
            self.__get()
        return self._z_dict.get('name')

    @name.setter
    def name(self, value: str):
        try:
            self.__update(name=value)
            self._z_dict['name'] = value
        except ZabbixAPIException as e:
            log.error("Ошибка смены имени: %s", e.data, extra=self.dict)

    @property
    def is_vip(self) -> str:
        if not self._vip:
            self._vip = self._get_VIP()
        return self._vip

    def _get_VIP(self) -> str:
        """Получение статуса коммутатора"""
        is_svip_macro = self.get_macro(r'{$IS_SVIP}')
        if is_svip_macro is not None:
            is_svip = is_svip_macro.value
            if is_svip and int(is_svip) == 1:
                return 'SVIP'
        is_vip_macro = self.get_macro(r'{$IS_VIP}')
        if is_vip_macro is not None:
            is_vip = is_vip_macro.value
            if is_vip and int(is_vip) == 1:
                return 'VIP'
        return ''

    @property
    def status(self) -> int:
        """0 -> активен, 1 -> не активен"""
        if self._z_dict.get('status') is None:
            self.__get()
        return int(self._z_dict.get('status'))

    @status.setter
    def status(self, value: int):
        self.__update(status=value)
        self._z_dict['status'] = value

    def is_monitored(self) -> bool:
        return self.status == 0

    @property
    def macros(self):
        if not self._macros:
            if not self._z_dict.get('macros'):
                self.__get(output='macros', selectMacros='extend')
            if self._z_dict.get('macros'):
                self._macros = [ZabbixMacro(self._zapi, m) for m in self._z_dict.get('macros')]
        return self._macros

    def get_macro(self, macro: str):
        """Получение пользовательского макроса (объект типа ZabbixMacro) """
        return next(filter(lambda m: m.name == macro, self.macros), None)  # первый найденный по имени

    @property
    def parent_templates(self):
        """Возвращает список привязанных шаблонов
        """
        if not self._z_dict.get('parentTemplates'):
            self.__get(output='parentTemplates', selectParentTemplates='extend')
        return (ZabbixTemplate(self._zapi, t) for t in self._z_dict.get('parentTemplates', []))

    def link_template(self, template: ZabbixTemplate):
        """Привязывает новый шаблон и удаляет все остальные (с очисткой) с этого узла"""
        self.__update(templates={'templateid': template.templateid},
                      templates_clear=[{'templateid': template.templateid} for template in self.parent_templates])
        self.__get(output='parentTemplates', selectParentTemplates='extend')

    def find_parent_templates(self, template_name: str):
        """Поиск шаблонов, начинающихся на указанный текст"""
        return filter(lambda t: re.match(template_name, t.host), self.parent_templates)

    @property
    def interfaces(self):
        if not self._interfaces or len(self._interfaces) != len(self._z_dict.get('interfaces')):
            if not self._z_dict.get('interfaces'):
                self.__get(output='interfaces', selectInterfaces='extend')
            self._interfaces = [ZabbixInterface(self._zapi, i) for i in self._z_dict.get('interfaces', []) if i]
        return self._interfaces

    def get_main_interface(self):
        main_interface = next(filter(lambda i: int(i.main) == 1, self.interfaces), None)
        return main_interface

    def get_ip(self):
        """Получение ip основного интерфейса"""
        return self.get_main_interface().ip

    @property
    def inventory(self) -> dict:
        if not self._z_dict.get('inventory'):
            self.__get(output='inventory', selectInventory='extend')
            del self._z_dict['inventory']['hostid']
            del self._z_dict['inventory']['inventory_mode']
        return self._z_dict.get('inventory')

    @inventory.setter
    def inventory(self, value: dict):
        log.info("Меняю инвентарные данные", extra=self.dict)
        self._z_dict['inventory'].update(value)
        self.__update(inventory=self._z_dict.get('inventory'))

    def update_or_create_macro(self, macro: str, value: str):
        """Обновить или создать новый макрос

        :param macro: Имя макроса
        :param value: Значение макросв
        :return:
        """
        zabbix_macro = self.get_macro(macro)
        if zabbix_macro:
            if str(zabbix_macro.value) != str(value):
                log.info("Меняю макрос", extra=self.dict)
                zabbix_macro.value = value
        else:
            log.info("Устанавливаю макрос", extra=self.dict)
            zabbix_macro = ZabbixMacro.create(self._zapi, self.hostid, macro, value)
        return zabbix_macro

    @zapi_exception("Ошибка удаления Zabbix узла")
    def delete(self):
        """УДАЛЕНИЕ Zabbix узла"""
        self._zapi.host.delete(self.hostid)

    @property
    def groups(self):
        if not self._groups:
            if not self._z_dict.get('groups'):
                self.__get(output='groups', selectGroups='extend')
            self._groups = (ZabbixGroup(self._zapi, group) for group in self._z_dict.get('groups'))
        return self._groups

    def get_group(self, name):
        return next(filter(lambda g: g.name == name, self.groups))

    @property
    def proxy_hostid(self) -> int:
        if not self._z_dict.get('proxy_hostid'):
            self.__get()
        return self._z_dict.get('proxy_hostid')

    @proxy_hostid.setter
    def proxy_hostid(self, value: int):
        log.info("Переношу на прокси", extra=self.dict)
        self.__update(proxy_hostid=value)
        self._z_dict['proxy_hostid'] = value

    @classmethod
    @zapi_exception("Ошибка создания Zabbix узла")
    def create(cls, zapi: ZabbixAPI, host: dict):
        """Создание нового узла в ZabbixAPI"""
        if not host.get('host') or not host.get('groups') or not host.get('interfaces'):
            raise KeyError
        z_hostid = zapi.host.create(**host)['hostids'][0]
        return cls(zapi, dict(hostid=z_hostid))


class ZabbixTrigger(Zabbix):
    """Класс для работы с узлами Zabbix"""

    def __init__(self, host: ZabbixHost, trigger: dict):
        """

        :param trigger: Триггер Zabbix.
            Обязательное поле 'triggerid'
        :rtype: ZabbixTrigger
        """
        if not trigger.get('triggerid'):
            raise KeyError
        super().__init__(host._zapi)
        self._host = host
        self._z_dict = trigger
        self._z_dict.update(host=self.host.dict.get('zabbix'))

    def __str__(self) -> str:
        return self.description

    @zapi_exception("Ошибка получения данных Zabbix триггера")
    def __get(self, **kwargs):
        """Получение всех данных триггера из ZabbixAPI"""
        trigger_get = dict(
            output='extend',
            triggerids=self._z_dict['triggerid'],
        )
        trigger_get.update(kwargs)
        z_trigger = self._zapi.trigger.get(**trigger_get)[0]
        self._z_dict.update(z_trigger)

    @property
    def triggerid(self) -> int:
        return int(self._z_dict['triggerid'])

    @property
    def value(self) -> int:
        if not self._z_dict.get('value'):
            self.__get()
        return int(self._z_dict.get('value'))

    @property
    def host(self) -> ZabbixHost:
        if self._host is None:
            self.__get()
            self._host = ZabbixHost(self._zapi, self._z_dict['host'])
        return self._host

    @property
    def description(self) -> str:
        if not self._z_dict.get('description'):
            self.__get()
        return self._z_dict.get('description')

    def get_dependencies(self):
        """Получение всех зависимых триггеров"""
        if not self._z_dict.get('dependencies'):
            self.__get(selectDependencies='extend')
        _dependencies: List[dict] = self._z_dict.get('dependencies')
        if not _dependencies:
            return None
        return (ZabbixTrigger(self.host, _dependency) for _dependency in _dependencies)

    @zapi_exception("Ошибка добавленя зависимостей Zabbix триггера")
    def add_dependencies(self, depends_on_triggerid: int):
        self._zapi.trigger.adddependencies({'triggerid': self.triggerid, 'dependsOnTriggerid': depends_on_triggerid})

    @zapi_exception("Ошибка удаления зависимостей Zabbix триггера")
    def delete_dependencies(self):
        """Удаляет все зависимости триггера"""
        del self._z_dict['dependencies']
        self._zapi.trigger.deleteDependencies({'triggerid': self.triggerid})


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
        self._z_dict = event

    def __str__(self) -> str:
        return f"{self.name} ({strftime(self.clock)})"

    @zapi_exception("Ошибка получения данных Zabbix события")
    def __get(self, **options):
        """Получение всех данных события из ZabbixAPI"""
        event_get = dict(
            output='extend',
            eventids=self._z_dict['eventid'],
        )
        event_get.update(options)
        z_event = self._zapi.event.get(**event_get)[0]
        self._z_dict.update(z_event)
        self._z_dict.update(trigger=self.trigger.dict.get('zabbix'))

    @property
    def eventid(self) -> int:
        return int(self._z_dict['eventid'])

    @property
    def clock(self) -> int:
        if not self._z_dict.get('clock'):
            self.__get()
        return int(self._z_dict.get('clock'))

    @property
    def trigger(self) -> ZabbixTrigger:
        return self._trigger

    @property
    def acknowledged(self):
        if not self._z_dict.get('acknowledged'):
            self.__get()
        return int(self._z_dict.get('acknowledged'))

    @property
    def messages(self) -> List[str]:
        if not self._z_dict.get('acknowledges'):
            self.__get(select_acknowledges='extend')
        acks = self._z_dict.get('acknowledges')
        return [m.get('message') for m in acks]

    @property
    def name(self):
        if not self._z_dict.get('name'):
            self.__get()
        return str(self._z_dict.get('name'))

    @property
    def value(self):
        if self._z_dict.get('value') is None:
            self.__get()
        return int(self._z_dict.get('value'))

    @property
    def tags(self) -> List[dict]:
        if not self._z_dict.get('tags'):
            self.__get(selectTags='extend')
        return self._z_dict.get('tags')

    @property
    def r_event(self):
        if not self._z_dict.get('r_eventid'):
            self.__get()
        event = ZabbixEvent(self.trigger, {'eventid': self._z_dict.get('r_eventid')})
        return event

    def get_tag(self, name: str) -> str:
        tag = next(filter(lambda t: t.get('tag') == name, self.tags), None)
        return tag.get('value', '')

    @zapi_exception("Ошибка подтверждения Zabbix события")
    def ack(self, message, action=6) -> bool:
        """Подтверждаем в Zabbix

        Возможные значения *action*:
            * 1 - закрыть проблемы
            * 2 - подтвердить событие
            * 4 - добавить сообщение
            * 8 - изменить важность
        :param str message: Текст сообщения
        :param int action: Сумма действий (например 7=1+2+4)
        """
        log.info("Подтверждение события в Zabbix", extra=self.dict)
        event_ack = dict(
            eventids=self._z_dict['eventid'],
            action=action,  # 2 - подтвердить событие, 4 - добавить сообщение
            message=message
        )
        self._zapi.event.acknowledge(**event_ack)
        self._z_dict['acknowledged'] = 1
        return True


class ZabbixProblem(ZabbixEvent):
    """Класс для работы с пролемами Zabbix"""

    pass
