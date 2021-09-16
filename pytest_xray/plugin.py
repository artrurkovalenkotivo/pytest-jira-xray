import os
from os import environ
from typing import List, Dict, Any, Union

import logging
import pytest

from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from _pytest.terminal import TerminalReporter
from _pytest.reports import TestReport

from .constant import (
    XRAY_MARKER_NAME,
)
from .helper import (
    Status,
    TestCase,
    TestExecution,
    datatypes_converter,
)
from .xray_publisher import XrayPublisher


class JiraXrayPlugin:

    def __init__(self, api_client, **kwargs):
        self.__testcase_jiraid_map = {}
        self._pytest_report = []
        self.__client: XrayPublisher = api_client
        self.__xr_execution_id = ""
        self.__xr_testplan_id = ""
        self.__interactive_mode = kwargs.get("interactive_push", False)
        self.__all_fails_allowed = kwargs.get("all_fails_allowed", False)
        self.__pytest_fields_to_push = kwargs.get("pytest_fields_to_push") or {}
        self.__osenv_fields_to_push = kwargs.get("osenv_fields_to_push") or {}
        self.__static_data = {}
        self.__log = logging.getLogger("JiraXrayPlugin")

    def __get_cli_and_ini_data(self, pytest_config):
        """
        method to get parameters from initial pytest configuration (static data)
        CLI has higher prio over INI

        Args:
            pytest_config: obj, instance of ConfParser from pytest context

        Returns:
            dict, dictionary of predefined parameters
        """
        options = vars(pytest_config.option)
        fields = self.__pytest_fields_to_push
        cli_and_ini_data = {}
        for py_name, field_name in fields.items():
            try:
                cli_and_ini_data[field_name] = options.get(py_name) or pytest_config.getini(py_name)
            except Exception:
                self.__log.error("Couldn't find cfg {}".format(field_name))
        cli_and_ini_data.update(suite=options['markexpr'])
        return cli_and_ini_data

    def __get_env_data(self):
        """
        method to extract attributes from os ENV

        Returns:
            dict
        """
        os_env_data = {}
        os_env = os.environ
        for os_arg_name, report_arg_name in self.__osenv_fields_to_push.items():
            os_env_data[report_arg_name] = os_env.get(os_arg_name)
        return os_env_data

    def __get_setting_data(self, pytest_config):
        """
        method to extract attributes from shared 'Settings' object
        Args:
            pytest_config: pytest config object

        Returns:
            dict
        """
        data = {}
        if hasattr(pytest_config, "Settings"):
            for settings_key, report_key in self.__pytest_fields_to_push.items():
                value = getattr(pytest_config.Settings, settings_key)
                if value:
                    data[report_key] = value
            if not data.get('build'):
                data['build'] = pytest_config.Settings.aut_build
        return data

    def __get_static_data(self, pytest_config):
        """
        method to extract and cache static parameters of test run
        Args:
            pytest_config: pytest config object

        Returns:
            dict
        """
        if not self.__static_data:
            data = {}
            cli_parameters = self.__get_cli_and_ini_data(pytest_config)
            env_parameters = self.__get_env_data()
            settings_parameters = self.__get_setting_data(pytest_config)
            data.update(cli_parameters)
            data.update(env_parameters)
            data.update(settings_parameters)
            self.__static_data = data
        else:
            data = self.__static_data
        return data

    def _get_pytest_report(self, pytest_report: TestReport, pytest_config, **kwargs):
        """
        Method to convert pytest report to a dictionary
        Args:
            pytest_report: TestReport, report
            pytest_config: pytest config object
            **kwargs:

        Returns:

        """
        py_execution_report = {}
        convert_datatypes = kwargs.get('convert_datatypes', True)
        static_data = self.__get_static_data(pytest_config)
        splt_test_name = pytest_report.nodeid.split('::')
        if len(splt_test_name) == 2:
            tc_module, tc_name = splt_test_name
        elif len(splt_test_name) >= 3:
            tc_module, tc_name = pytest_report.nodeid.split('::')[1:3]
        else:
            tc_module, tc_name = pytest_report.nodeid, pytest_report.nodeid
        if len(pytest_report.longreprtext) > 5000:
            longreprtext = pytest_report.longreprtext[:2000] + " TRUNCATED " + pytest_report.longreprtext[-3000:]
        else:
            longreprtext = pytest_report.longreprtext

        if pytest_report.passed:
            status = "passed"
        elif pytest_report.failed:
            status = "failed"
        elif pytest_report.skipped:
            status = "skipped"
        else:
            status = "None"
        if pytest_report.user_properties:
            error_signature = pytest_report.user_properties.get("error_signature")
            py_execution_report.update(error_signature=error_signature)
        py_execution_report.update(status=status,
                                   longreprtext=longreprtext,
                                   execution_time=pytest_report.duration,
                                   tc_name=tc_name,
                                   jira_id=self.__testcase_jiraid_map[pytest_report.nodeid],
                                   )

        py_execution_report.update(static_data)

        if convert_datatypes:
            py_execution_report = datatypes_converter(py_execution_report)
        self.__log.debug("Generated payload: {}".format(py_execution_report))
        return py_execution_report

    def _generate_xray_execution_report(self, report: Union[dict, list]):
        """
        Method to convert pytest report to xray test execution
        Args:
            report: dict/list, representation of pytest report

        Returns:
            TestExecution: generated object will all executions
        """
        # self.__xr_execution_id - dynamically updates after interactive mode push
        xray_test_execution = TestExecution(test_execution_key=self.__xr_execution_id,
                                            test_plan_key=self.__xr_testplan_id)
        if isinstance(report, dict):
            report = [report]

        for test in report:
            status = test["status"]
            jira_id = test["jira_id"]
            longreprtext = test.get("longreprtext")
            if 'passed' in status:
                tc = TestCase(jira_id, Status.PASS)
            elif 'failed' in status:
                tc = TestCase(jira_id, Status.FAIL, longreprtext)
            elif 'skipped' in status:
                tc = TestCase(jira_id, Status.ABORTED, longreprtext)
            else:
                raise ValueError("Unsupported execution status: '{}'".format(test["status"]))
            xray_test_execution.append(tc)
        return xray_test_execution

    def _push_report(self, report: TestExecution):
        """
        Method to push report to Jira
        Args:
            report: TestExecution, object with case execution details

        Returns:
            str, ID of test execution
        """
        return self.__client.publish(report)

    # pytest hooks part
    # =============================================================
    def pytest_report_header(self, config, startdir):
        """ Add extra-info in header """
        message = '[JiraXrayPlugin]:  Plugin is enabled.'
        return message

    def pytest_collection_modifyitems(self, config: Config, items: List[Item]) -> None:
        """
        pytest hook for collecting cases. On the step we extract Xray markers
        """
        for item in items:
            # associate test cases with JiraID from Xray markers
            marker = item.get_closest_marker(XRAY_MARKER_NAME)
            if marker:
                test_key = marker.args[0]
                self.__testcase_jiraid_map[item.nodeid] = test_key

    @pytest.mark.hookwrapper
    def pytest_runtest_makereport(self, item, call):
        """
        Generate report after each tc execution
        Args:
            item: : pytest item object
            call: : pytest call object

        Returns:
            None
        """
        outcome = yield
        report = outcome.get_result()

        if report.when == 'setup' and (report.skipped or report.failed):
            if report.nodeid in self.__testcase_jiraid_map:
                pytest_report = self._get_pytest_report(report, item.config)
                self._pytest_report.append(pytest_report)
                if self.__interactive_mode:
                    xray_execution = self._generate_xray_execution_report(pytest_report)
                    exec_id = self._push_report(xray_execution)
                    # this is needed to update execId for _generate_xray_execution_report() function
                    self.__xr_execution_id = exec_id
        elif report.when == 'call':
            if report.nodeid in self.__testcase_jiraid_map:
                pytest_report = self._get_pytest_report(report, item.config)
                self._pytest_report.append(pytest_report)
                if self.__interactive_mode:
                    xray_execution = self._generate_xray_execution_report(pytest_report)
                    exec_id = self._push_report(xray_execution)
                    # this is needed to update execId for _generate_xray_execution_report() function
                    self.__xr_execution_id = exec_id
            else:
                self.__log.info("{} doesnt contain Xray marker".format(report.nodeid))

    # temporary removed
    # def pytest_terminal_summary(self, terminalreporter: TerminalReporter) -> None:
    #     """
    #     Pytest hook. For non-interactive report generation
    #     """
    #     pass

    def pytest_sessionfinish(self, session, exitstatus):
        """
        pytest hook on the end of test run. In the place we push all report in non-interactive mode
        """
        is_passed = any(case.get('status') == "passed" for case in self._pytest_report)
        if not self.__interactive_mode:
            if is_passed or (self.__all_fails_allowed is not is_passed):
                xray_execution = self._generate_xray_execution_report(self._pytest_report)
                self._push_report(xray_execution)
            else:
                print("\n[JiraXrayPlugin] There are no passed cases. By config zero-pass runs prohibited to push")
        print("\n[JiraXrayPlugin] Report sync finished. Total items: '{}'".format(len(self._pytest_report)))
        if self.__client.errors:
            print("\n[JiraXrayPlugin] Report sync failed: {} times".format(len(self.__client.errors)))
            print("\n[JiraXrayPlugin] Errors: {}".format("\n".join(self.__client.errors)))
