import datetime as dt
import enum
import configparser
import os
import re
from typing import List, Dict, Union, Any

from .constant import XRAY_MARKER_NAME, DATETIME_FORMAT, PREFIX, XRAY_CONFIG

_test_keys = {}


class Status(str, enum.Enum):
    TODO = 'TODO'
    EXECUTING = 'EXECUTING'
    PENDING = 'PENDING'
    PASS = 'PASS'
    FAIL = 'FAIL'
    ABORTED = 'ABORTED'
    BLOCKED = 'BLOCKED'


class TestCase:

    def __init__(self,
                 test_key: str,
                 status: str,
                 comment: str = None,
                 duration: float = 0.0):
        self.test_key = test_key
        self.status = Status(status)
        self.comment = comment or ''
        self.duration = duration

    def as_dict(self) -> Dict[str, str]:
        return dict(testKey=self.test_key,
                    status=self.status,
                    comment=self.comment)


class TestExecution:

    def __init__(self,
                 test_execution_key: str = None,
                 test_plan_key: str = None,
                 user: str = None,
                 revision: str = None,
                 tests: List = None):
        self.test_execution_key = test_execution_key
        self.test_plan_key = test_plan_key or ''
        self.user = user or ''
        self.revision = revision or ''
        self.start_date = dt.datetime.now(tz=dt.timezone.utc)
        self.tests = tests or []

    def append(self, test: Union[dict, TestCase]) -> None:
        if not isinstance(test, TestCase):
            test = TestCase(**test)
        self.tests.append(test)

    def as_dict(self) -> Dict[str, Any]:
        tests = [test.as_dict() for test in self.tests]
        info = dict(startDate=self.start_date.strftime(DATETIME_FORMAT),
                    finishDate=dt.datetime.now(tz=dt.timezone.utc).strftime(DATETIME_FORMAT))
        data = dict(info=info,
                    tests=tests)
        if self.test_plan_key:
            info['testPlanKey'] = self.test_plan_key
        if self.test_execution_key:
            data['testExecutionKey'] = self.test_execution_key
        return data


class ConfigManager:
    def __init__(self, pytest_config):
        self._cfg_file = None
        self._pytest_config = pytest_config
        cfg_file_path = self._getconfigfile(XRAY_CONFIG)
        if os.path.isfile(cfg_file_path) or os.path.islink(cfg_file_path):
            self._cfg_file = configparser.ConfigParser()
            self._cfg_file.read(cfg_file_path)

    def _get_from_cfg(self, name, section=None, default=None, flag=False, **kwargs):
        """
        method to get data from Xray plugin cfg file
        Args:
            name: str, name of parameter
            section: str, ini section
            default: default value
            flag: bool, flag or not
            **kwargs:

        Returns:
            str
        """
        if self._cfg_file:
            name = name.replace(PREFIX, '')
            if section and self._cfg_file.has_section(section):
                value = self._cfg_file.getboolean(section, name) if flag else self._cfg_file.get(section, name)
            else:
                sections = self._cfg_file.sections()
                for section in sections:
                    if self._cfg_file.has_option(section, name):
                        value = self._cfg_file.get(section, name)
                        break
                else:
                    value = default
        else:
            value = default
        return value

    def _get_from__pytest_cli(self, name: str, default=None, flag=False, **kwargs):
        if name:
            if not name.startswith('--'):
                name = '--{}'.format(name)
            value = self._pytest_config.getoption(name, default)
        else:
            value = default
        return value

    def _get_from_pytest_ini(self, name: str, default=None, flag=False, **kwargs):
        if name:
            if name.startswith('--'):
                name = name.replace('--', '')
            try:
                value = self._pytest_config.getini(name)
            except ValueError:
                value = default
        else:
            value = default
        if flag:
            value = self.__covert_to_bool(value)
        return value

    def __covert_to_bool(self, value):
        if isinstance(value, str) and value.strip() in ('false', 'False', 'FALSE'):
            value = False
        else:
            value = bool(value)
        return value

    def _getconfigfile(self, option_name, default="") -> str:
        """
        Method to get path to Xray plugin configfile
        Args:
            option_name: str, name of option
            default: str, default value

        Returns:
            str
        """
        GETTERS = [
            self._get_from__pytest_cli,
            self._get_from_pytest_ini,
        ]
        for getter in GETTERS:
            try:
                value = getter(name=option_name)
            except ValueError:
                value = None
            if value:
                break
        else:
            value = default
        return value

    def getoption(self, opt_name=None, section=None, default=None, flag=False):
        """
        Method to get parameter from any available source: pytest CLI, pytest.ini, config file in the prio
        Args:
            opt_name: str, name of option
            section: str, section in cfg/ini file if exists
            default: any, default value of option if it is not defined
            flag: bool, True if parameter must be bool

        Returns:
            str/bool
        """
        GETTERS = [
            self._get_from__pytest_cli,
            self._get_from_pytest_ini,
            self._get_from_cfg,
        ]
        for getter in GETTERS:
            try:
                value = getter(name=opt_name, secton=section, flag=flag)
            except ValueError:
                value = None
            if value:
                break
        else:
            value = default
        if flag and value and not isinstance(value, bool):
            value = self.__covert_to_bool(value)
        return value

    def get_list(self, option: str) -> list:
        """
        Method to get list values from DBSync plugin config file ONLY
        Args:
            option: str, name of option

        Returns:
            list
        """
        raw_value = self._get_from_cfg(option)
        if raw_value:
            list_of_marks = raw_value.split('\n')
        else:
            list_of_marks = []
        return list_of_marks

    def get_dict(self, option_name: str) -> dict:
        """
        Method to get dict values from DBSync plugin config file ONLY
        dict will be generated from lines split by ':' symbol
        Args:
            option_name: str, name of option

        Returns:
            dict
        """
        raw_value = self._get_from_cfg(option_name)
        output_dict = {}
        if raw_value:
            for line in raw_value.split('\n'):
                key, _, value = line.partition(":")
                if not value:
                    value = key
                output_dict[key.strip()] = value.strip()
        return output_dict


def datatypes_converter(payload: dict):
        TRUE = 'true'
        FALSE = 'false'
        result = {}
        for key, value in payload.items():
            if value in (TRUE, FALSE):
                if value == TRUE:
                    value = True
                elif value == FALSE:
                    value = False
            elif re.match(r"^\d+\.\d+$", str(value)):
                value = float(value)
            elif re.match(r"^\d+$", str(value)):
                value = int(value)
            result[key] = value
        return result