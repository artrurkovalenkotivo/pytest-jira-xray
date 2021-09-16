import pytest_xray.constant as constants
from .xray_publisher import XrayPublisher, PrintPublisher
from pytest_xray.plugin import JiraXrayPlugin
from pytest_xray.helper import ConfigManager

OPTS = constants.OPTS


def pytest_addoption(parser):
    group = parser.getgroup('pytest-xray')
    group.addoption(
        f'--{constants.ENABLE}',
        action='store_true',
        help='Push testruns to XRAY')
    group.addoption(
        f'--{OPTS.CONFIG}',
        action='store',
        default=None,
        help='Path to the config file containing information about the XRAY server')
    group.addoption(
        f'--{OPTS.USERNAME}',
        action='store',
        default=None,
        help='Username for authentication')
    group.addoption(
        f'--{OPTS.PASSWORD}',
        action='store',
        default=None,
        help='Password for authentication')
    group.addoption(
        f'--{OPTS.URL}',
        action='store',
        default=None,
        help='url or hostname to Server')
    group.addoption(
        f'--{OPTS.PORT}',
        action='store',
        default=None,
        help='Server connection PORT')
    group.addoption(
        f'--{OPTS.TIMEOUT}',
        action='store',
        default=None,
        help='XRAY connection timeout')
    group.addoption(
        f'--{OPTS.INTERACTIVE}',
        action='store',
        default=None,
        help='Push report after each TC or on on the end of test run')
    group.addoption(
        f'--{OPTS.ALL_FAILS_ALLOWED}',
        action='store',
        default=None,
        help='Push report only if at least one test passed (filter broken runs). '
             'works with xr_interactive_push=true only')

    parser.addini(OPTS.CONFIG, 'Path to the config file containing information about the XRAY server')
    parser.addini(OPTS.USERNAME, 'Username for XRAY authentication')
    parser.addini(OPTS.PASSWORD, 'Passord for XRAY authentication')
    parser.addini(OPTS.URL, 'url or hostname to XRAY')
    parser.addini(OPTS.PORT, 'port or hostname to XRAY')
    parser.addini(OPTS.TIMEOUT, 'XRAY connection timeout')
    parser.addini(OPTS.INTERACTIVE, 'Push report after each TC or on on the end of test run')
    parser.addini(OPTS.ALL_FAILS_ALLOWED, 'Push report only if at least one test passed (filter broken runs).')


def pytest_configure(config):
    if config.getoption(f'--{constants.ENABLE}'):
        config_manager = ConfigManager(config)
        # client = XrayPublisher(base_url=config_manager.getoption(OPTS.URL),
        #                        auth=(config_manager.getoption(OPTS.USERNAME),
        #                              config_manager.getoption(OPTS.PASSWORD)),
        #                        verify=config_manager.getoption(OPTS.SSL_VERIFICATION, default=False, flag=True),
        #                        )
        client = PrintPublisher(base_url=config_manager.getoption(OPTS.URL),
                                auth=(config_manager.getoption(OPTS.USERNAME),
                                      config_manager.getoption(OPTS.PASSWORD)),
                                verify=config_manager.getoption(OPTS.SSL_VERIFICATION, default=False, flag=True),
                                )
        config.pluginmanager.register(
            JiraXrayPlugin(api_client=client,
                           interactive_push=config_manager.getoption(OPTS.INTERACTIVE, default=False, flag=True),
                           all_fails_allowed=config_manager.getoption(OPTS.ALL_FAILS_ALLOWED, default=False, flag=True),
                           pytest_fields_to_push=config_manager.get_dict(OPTS.PYTEST_FIELDS),
                           osenv_fields_to_push=config_manager.get_dict(OPTS.OSENV_FIELDS),
                           ),
            # Name of plugin instance (allow to be used by other plugins)
            name=constants.XRAY_PLUGIN
        )
        config.addinivalue_line(
            'markers', f'{constants.XRAY_MARKER_NAME}(JIRA_ID): mark test with JIRA XRAY test case ID'
        )
