import logging
import re
import time
from typing import List

from pyzabbix import ZabbixAPI, ZabbixAPIException

log = logging.getLogger(__name__)


def zapi_exception(log_message: str):
    """Создание декоратора с заданным сообщение в лог"""

    def decorator(func):

        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ZabbixAPIException, IndexError) as e:
                log.error("%s: %s", log_message, e.data)

        return wrapper

    return decorator


class Zabbix:
    """Общий класс для хранения ссылки на ZabbixAPI"""

    def __init__(self, zapi: ZabbixAPI):
        """

        :param zapi: ссылка на объект ZabbixAPI
        """
        self._zapi = zapi

    @property
    def zapi(self):
        return self._zapi


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
        self._z_proxy = proxy

    @zapi_exception("Ошибка получения данных Zabbix прокси")
    def _get(self, **options):
        proxy_get = dict(
            output='extend',
            proxyids=self._z_proxy['proxyid'],
        )
        proxy_get.update(options)
        z_proxy = self._zapi.proxy.get(proxy_get)[0]
        self._z_proxy.update(z_proxy)

    @property
    def proxyid(self):
        return self._z_proxy.get('proxyid')

    @property
    def host(self):
        if not self._z_proxy.get('host'):
            self._get()
        return self._z_proxy.get('host')

    @property
    def status(self):
        if not self._z_proxy.get('status'):
            self._get()
        return self._z_proxy.get('status')


class ZabbixGroup(Zabbix):
    """Класс для работы с группами узлов Zabbix"""

    @property
    def groupid(self):
        return int(self._z_group['groupid'])

    @property
    def name(self):
        if not self._z_group.get('name'):
            self._get()
        return self._z_group.get('name')

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

    def __str__(self) -> str:
        return self._z_group.get('name')

    @zapi_exception("Ошибка получения данных Zabbix группы")
    def _get(self, **options):
        hostgroup_get = dict(
            output='extend',
            groupids=self._z_group['groupid'],
        )
        hostgroup_get.update(options)
        z_group = self._zapi.hostgroup.get(**hostgroup_get)[0]
        self._z_group.update(z_group)

    @classmethod
    @zapi_exception("Ошибка получения Zabbix группы")
    def get_by_id(cls, zapi: ZabbixAPI, groupid: int):
        """Создание объекта ZabbixGroup из ZabbixAPI"""
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
            raise KeyError
        super().__init__(zapi)
        self._z_macro = macro

    def __str__(self):
        return self.name

    @zapi_exception("Ошибка получения данных макроса Zabbix")
    def _get(self):
        """Получение всех данных макроса из ZabbixAPI"""
        usermacro_get = dict(
            output='extend',
            hostmacroids=[self._z_macro['hostmacroid']],
        )
        z_macro = self._zapi.usermacro.get(**usermacro_get)[0]
        self._z_macro.update(z_macro)

    @zapi_exception("Ошибка обновления данных макроса")
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
        self._z_macro['macro'] = value

    @property
    def value(self) -> str:
        if not self._z_macro.get('value'):
            self._get()
        return self._z_macro.get('value')

    @value.setter
    def value(self, value: str):
        self._update(value=value)
        self._z_macro['value'] = value

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
        self._z_template = template

    def __str__(self) -> str:
        return self.name

    @zapi_exception("Ошибка получения данных макроса Zabbix")
    def _get(self):
        """Получение всех данных шаблона"""
        template_get = dict(
            output='extend',
            templateids=self._z_template.get('templateid'),
        )
        z_template = self._zapi.template.get(**template_get)[0]
        self._z_template.update(z_template)

    @property
    def templateid(self):
        return self._z_template['templateid']

    @property
    def host(self) -> str:
        if not self._z_template.get('host'):
            self._get()
        return self._z_template.get('host')

    @property
    def name(self) -> str:
        if not self._z_template.get('name'):
            self._get()
        return self._z_template.get('name')

    @property
    def description(self) -> str:
        if not self._z_template.get('description'):
            self._get()
        return self._z_template.get('description')


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

    @zapi_exception("Ошибка получения данных Zabbix интерфейса")
    def _get(self, **kwargs):
        """Получение всех данных интерфейса из ZabbixAPI"""
        interface_get = dict(
            output='extend',
            interfaceid=self._z_interface.get('interfaceid')
        )
        interface_get.update(kwargs)
        z_interface = self._zapi.hostinterface.get(**interface_get)[0]
        self._z_interface.update(z_interface)

    @zapi_exception("Ошибка обновления данных Zabbix интерфейса")
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
    def ip(self, value: str):
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

    @zapi_exception("Ошибка получения данных Zabbix узла")
    def _get(self, **options):
        """Получение всех данных узла из ZabbixAPI"""
        host_get = dict(
            output='extend',
            hostids=self._z_host['hostid'],
        )
        host_get.update(options)
        z_host = self._zapi.host.get(**host_get)[0]
        self._z_host.update(z_host)

    def _update(self, **options):
        """Обновление данных узла в ZabbixAPI"""
        host_update = dict(
            hostid=self._z_host['hostid'],
        )
        host_update.update(options)
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
        try:
            self._update(host=value)
            self._z_host['host'] = value
        except ZabbixAPIException as e:
            log.error("%s: Ошибка переименовывания: %s", self, e.data)

    @property
    def name(self) -> str:
        if self._z_host.get('name') is None:
            self._get()
        return self._z_host.get('name')

    @name.setter
    def name(self, value: str):
        try:
            self._update(name=value)
            self._z_host['name'] = value
        except ZabbixAPIException as e:
            log.error("%s: Ошибка смены имени: %s", self, e.data)

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
            raise KeyError
        super().__init__(zapi)
        self._z_host = host
        self._macros = list()  # список ZabbixMacro
        self._interfaces = list()  # список ZabbixInterface
        self._vip = None
        self._groups = None

    def __str__(self) -> str:
        return self.host

    @classmethod
    @zapi_exception("Ошибка получения Zabbix узла")
    def get_by_id(cls, zapi: ZabbixAPI, hostid: int):
        """Создание объекта ZabbixHost из ZabbixAPI"""
        host_get = dict(
            output='extend',
            hostids=hostid,
        )
        z_host: dict = zapi.host.get(**host_get)[0]
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
        """0 -> активен, 1 -> не активен"""
        if self._z_host.get('status') is None:
            self._get()
        return int(self._z_host.get('status'))

    @status.setter
    @zapi_exception("Ошибка смены статуса")
    def status(self, value: int):
        self._update(status=value)
        self._z_host['status'] = value

    def is_monitored(self) -> bool:
        return self.status == 0

    @property
    def macros(self):
        if not self._macros:
            if not self._z_host.get('macros'):
                self._get(output='macros', selectMacros='extend')
            self._macros = [ZabbixMacro(self._zapi, m) for m in self._z_host.get('macros')]
        return self._macros

    def get_macro(self, macro: str):
        """Получение пользовательского макроса (объект типа ZabbixMacro) """
        return next(filter(lambda m: m.name == macro, self.macros), None)  # первый найденный по имени

    @property
    def parent_templates(self):
        """Возвращает список привязанных шаблонов
        """
        if not self._z_host.get('parentTemplates'):
            self._get(output='parentTemplates', selectParentTemplates='extend')
        return (ZabbixTemplate(self._zapi, t) for t in self._z_host.get('parentTemplates'))

    @zapi_exception("Ошибка привязки шаблона")
    def link_template(self, template: ZabbixTemplate):
        """Привязывает новый шаблон и удаляет все остальные с этого узла"""
        self._update(templates=template.templateid)
        self._get(output='parentTemplates', selectParentTemplates='extend')

    def find_parent_templates(self, template_name: str):
        """Поиск шаблонов, начинающихся на указанный текст"""
        return filter(lambda t: re.match(template_name, t.host), self.parent_templates)

    @property
    def interfaces(self):
        if not self._interfaces or len(self._interfaces) != len(self._z_host.get('interfaces')):
            if not self._z_host.get('interfaces'):
                self._get(output='interfaces', selectInterfaces='extend')
            self._interfaces = [ZabbixInterface(self._zapi, i) for i in self._z_host.get('interfaces')]
        return self._interfaces

    def get_main_interface(self):
        main_interface = next(filter(lambda i: int(i.main) == 1, self.interfaces), None)
        return main_interface

    def get_ip(self):
        """Получение ip основного интерфейса"""
        return self.get_main_interface().ip

    @property
    def inventory(self) -> dict:
        if not self._z_host.get('inventory'):
            self._get(output='inventory', selectInventory='extend')
            del self._z_host['inventory']['hostid']
            del self._z_host['inventory']['inventory_mode']
        return self._z_host.get('inventory')

    @inventory.setter
    @zapi_exception("Ошибка обновления инвентарных данных")
    def inventory(self, value: dict):
        log.info("%12s: Меняю инвентарные данные %s", self, ','.join(value.keys()))
        self._z_host['inventory'].update(value)
        self._update(inventory=self._z_host.get('inventory'))

    @zapi_exception("Ошибка установки макроса")
    def update_or_create_macro(self, macro: str, value: str):
        """Обновить или создать новый макрос

        :param macro: Имя макроса
        :param value: Значение макросв
        :return:
        """
        zabbix_macro = self.get_macro(macro)
        if zabbix_macro:
            if str(zabbix_macro.value) != str(value):
                log.info("%12s: Меняю макрос %s с '%s' на '%s'", self, macro, zabbix_macro.value, value)
                zabbix_macro.value = value
        else:
            log.info("%12s: Устанавливаю макрос '%s' в '%s'", self, macro, value)
            zabbix_macro = ZabbixMacro.create(self._zapi, self.hostid, macro, value)
        return zabbix_macro

    def delete(self):
        """УДАЛЕНИЕ Zabbix узла"""
        self._zapi.host.delete(self.hostid)

    @property
    def groups(self):
        if not self._groups:
            if not self._z_host.get('groups'):
                self._get(output='macros', selectMacros='extend')
            self._groups = [ZabbixGroup(self._zapi, group) for group in self._z_host.get('groups')]
        return self._groups

    def get_group(self, name):
        return next(filter(lambda g: g.name == name, self.groups))

    @property
    def proxy_hostid(self) -> int:
        if not self._z_host.get('proxy_hostid'):
            self._get()
        return self._z_host.get('proxy_hostid')

    @proxy_hostid.setter
    @zapi_exception("Ошибка переноса на прокси")
    def proxy_hostid(self, value: int):
        log.info("%12s: Переношу на прокси: %s", self, str(value))
        self._update(proxy_hostid=value)
        self._z_host['proxy_hostid'] = value


class ZabbixTrigger(Zabbix):
    """Класс для работы с узлами Zabbix"""

    def is_trigger_A4(self):
        """Триггер по недоступности A4?"""
        return re.match(r'^A4-[0-9]{5}-', str(self._host)) and re.search(r'Коммутатор недоступен', self.description)

    def is_trigger_D4(self):
        """Триггер по недоступности D4?"""
        return re.match(r'^D4-', str(self._host))

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

    def is_trigger_mass_cut(self):
        """Триггер по массовым порезам?"""
        return re.search(r'Массовый порез', self.description)

    def __init__(self, host: ZabbixHost, trigger: dict):
        """

        :param trigger: Триггер Zabbix.
            Обязательное поле 'triggerid'
        :rtype: ZabbixTrigger
        """
        if not trigger.get('triggerid'):
            raise KeyError
        super().__init__(host.zapi)
        self._z_trigger = trigger
        self._host = host

    def __str__(self) -> str:
        return self.description

    @zapi_exception("Ошибка получения данных Zabbix триггера")
    def _get(self, **kwargs):
        """Получение всех данных триггера из ZabbixAPI"""
        trigger_get = dict(
            output='extend',
            triggerids=self._z_trigger['triggerid'],
        )
        trigger_get.update(kwargs)
        z_trigger = self._zapi.trigger.get(**trigger_get)[0]
        self._z_trigger.update(z_trigger)

    @classmethod
    @zapi_exception("Ошибка получения Zabbix триггера")
    def get_by_id(cls, zapi: ZabbixAPI, triggerid: int):
        trigger_get = dict(
            output='extend',
            triggerids=[triggerid],
            expandExpression='true',
            expandDescription='true',
            expandData='true',
            selectHosts='extend',
        )
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

    def get_dependencies(self):
        """Получение всех зависимых триггеров"""
        if not self._z_trigger.get('dependencies'):
            self._get(selectDependencies='extend')
        _dependencies: List[dict] = self._z_trigger.get('dependencies')
        if not _dependencies:
            return None
        return (ZabbixTrigger(self.host, _dependency) for _dependency in _dependencies)

    def add_dependencies(self, depends_on_triggerid: int):
        self._zapi.trigger.adddependencies({'triggerid': self.triggerid, 'dependsOnTriggerid': depends_on_triggerid})

    @zapi_exception("Ошибка удаления зависимостей Zabbix триггера")
    def delete_dependencies(self):
        """Удаляет все зависимости триггера"""
        del self._z_trigger['dependencies']
        self._zapi.trigger.deleteDependencies({'triggerid': self.triggerid})

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
        return (e.get('message') for e in z_events if e.get('message'))


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
        super().__init__(trigger.zapi)
        self._trigger = trigger
        self._z_event = event

    def __str__(self) -> str:
        return self.name

    @zapi_exception("Ошибка получения данных Zabbix события")
    def _get(self, **options):
        """Получение всех данных события из ZabbixAPI"""
        event_get = dict(
            output='extend',
            eventids=self._z_event['eventid'],
        )
        event_get.update(options)
        z_event = self._zapi.event.get(**event_get)[0]
        self._z_event.update(z_event)

    @classmethod
    @zapi_exception("Ошибка получения Zabbix события")
    def get_by_id(cls, zapi: ZabbixAPI, eventid: int):
        """Создание объекта ZabbixEvent из ZabbixAPI"""
        event_get = dict(
            output='extend',
            eventids=[eventid],
        )
        z_event = zapi.event.get(**event_get)[0]
        trigger = ZabbixTrigger.get_by_id(zapi, z_event['objectid'])
        if trigger:
            return cls(trigger, z_event)
        return None

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

    @property
    def name(self):
        if not self._z_event.get('name'):
            self._get()
        return str(self._z_event.get('name'))

    @property
    def tags(self) -> List[dict]:
        if not self._z_event.get('tags'):
            self._get(selectTags='extend')
        return self._z_event.get('tags')

    def get_tag(self, name: str) -> str:
        return next(filter(lambda t: t.get('tag') == name, self.tags)).get('value')

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
        log.debug("%s: Подтверждение события в Zabbix")
        event_ack = dict(
            eventids=self._z_event['eventid'],
            action=action,  # 2 - подтвердить событие, 4 - добавить сообщение
            message=message
        )
        self._zapi.event.acknowledge(**event_ack)
        self._z_event['acknowledged'] = 1
        return True


class ZabbixProblem(ZabbixEvent):
    """Класс для работы с пролемами Zabbix"""

    @zapi_exception("Ошибка получения данных Zabbix проблемы")
    def _get(self, **options):
        """Получение всех данных события из ZabbixAPI"""
        problem_get = dict(
            output='extend',
            eventids=self._z_event['eventid'],
        )
        problem_get.update(options)
        z_event = self._zapi.problem.get(**problem_get)[0]
        self._z_event.update(z_event)

    @classmethod
    @zapi_exception("Ошибка получения Zabbix проблемы")
    def get_by_id(cls, zapi: ZabbixAPI, eventid: int):
        """Создание объекта ZabbixEvent из ZabbixAPI"""
        event_get = dict(
            output='extend',
            eventids=[eventid],
        )
        z_event = zapi.problem.get(**event_get)[0]
        trigger = ZabbixTrigger.get_by_id(zapi, z_event['objectid'])
        if trigger:
            return cls(trigger, z_event)
        return None
