import logging
from typing import Union

import requests
from requests.auth import AuthBase

from .constant import TEST_EXECUTION_ENDPOINT
from .helper import TestExecution

logging.basicConfig()


class XrayError(Exception):
    """Custom exception for Jira XRAY"""


class PrintPublisher:

    def __init__(self,
                 base_url: str,
                 auth: Union[AuthBase, tuple],
                 verify: Union[bool, str] = True) -> None:
        self.errors = []

    def publish(self, test_execution: TestExecution) -> str:
        import pprint
        print("\n")
        pprint.pprint(test_execution.as_dict())
        return "local"


class XrayPublisher:

    def __init__(self,
                 base_url: str,
                 auth: Union[AuthBase, tuple],
                 verify: Union[bool, str] = True) -> None:
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.auth = auth
        self.verify = verify
        self._log = logging.getLogger(__name__)
        self.errors = []

    @property
    def endpoint_url(self) -> str:
        return self.base_url + TEST_EXECUTION_ENDPOINT

    def publish_xray_results(self, url: str, auth: AuthBase, data: dict) -> dict:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request(method='POST', url=url, headers=headers, json=data,
                                        auth=auth, verify=self.verify)
        except requests.exceptions.ConnectionError as e:
            self._log.exception('ConnectionError to JIRA service %s', self.base_url)
            raise XrayError(e)
        else:
            try:
                response.raise_for_status()
            except Exception as e:
                self._log.error('Could not post to JIRA service %s. Response status code: %s',
                              self.base_url, response.status_code)
                raise XrayError from e
            return response.json()

    def publish(self, test_execution: TestExecution) -> str:
        """
        Publish results to Jira.

        :param test_execution: instance of TestExecution class
        :return: test execution issue id
        """
        try:
            result = self.publish_xray_results(self.endpoint_url, self.auth, test_execution.as_dict())
        except XrayError as e:
            self.errors.append(f"{e}")
            return ''
        else:
            key = result['testExecIssue']['key']
            self._log.info('Uploaded results to JIRA XRAY Test Execution: %s', key)
            return key
