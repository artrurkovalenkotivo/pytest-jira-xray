# pytest-xray-sync

pytest-jira-xray is a plugin for pytest that uploads test results to JIRA XRAY.

### Installation

```commandline
pip install pytest-xray-sync
```

or

```commandline
python setup.py install
```

### Usage

Mark a test with JIRA XRAY test ID

```python
# -- FILE: test_example.py
import pytest

@pytest.mark.xray('JIRA-1')
def test_one():
    assert True
```

Configure plugin:
There are 3 ways to configure plugin:
* command line arguments
* pytest.ini
* dedicated ini file with XRAY config only

For pytest.ini or CLI for each option **xr_** prefix must be added
```ini
# kind of mandatory
url = https://link to jira
port = 9999
username = name
password = pass

# Optional
xr_testplan = plan id
xr_execution_id = execution id

all_fails_allowed = True/False
interactive_push = True/False

osenv_fields_to_push = 
    OS_ENV_NAME: NAME_FOR_REPORT,
    OS_ENV_NAME2: NAME_FOR_REPORT2
    
pytest_fields_to_push = 
    pytest_var_name: NAME_FOR_REPORT,
    pytest_var_name2: NAME_FOR_REPORT2

ssl_verification = True/False
timeout = 30

```


Upload results to new test execution:
```commandline
pytest . --xray-sync
```

To use dedicated configfile for the plugin
```commandline
pytest . --xray-sync --xr_config /home/test/xray_config.cfg
```

