TEST_EXECUTION_ENDPOINT = '/rest/raven/2.0/import/execution'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
XRAY_PLUGIN = "JIRA_XRAY"
XRAY_MARKER_NAME = "xray"
PREFIX = 'xr_'
XRAY_CONFIG = 'xr_config'
ENABLE = 'xray-sync'


class MetaData(type):
    """ MetaClass for Constant storing"""

    def __iter__(self):
        for attr in dir(self):
            if not attr.startswith("__"):
                yield self.__dict__[attr]


class OPTS(metaclass=MetaData):
    USERNAME = 'xr_username'
    PASSWORD = 'xr_password'
    URL = 'xr_url'
    PORT = "xr_port"
    TIMEOUT = 'xr_timeout'
    XRAY_EXECUTION_ID = 'xr_testplan'
    XRAY_TEST_PLAN_ID = "xr_execution_id"
    INTERACTIVE = 'xr_interactive_push'
    ALL_FAILS_ALLOWED = 'xr_all_fails_allowed'
    PYTEST_FIELDS = 'xr_pytest_fields_to_push'
    OSENV_FIELDS = 'xr_osenv_fields_to_push'
    CONFIG = XRAY_CONFIG
    SSL_VERIFICATION = "xr_ssl_verification"
