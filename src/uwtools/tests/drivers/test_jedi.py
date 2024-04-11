# pylint: disable=missing-function-docstring,protected-access,redefined-outer-name
"""
JEDI driver tests.
"""
import datetime as dt
import logging
from pathlib import Path
from unittest.mock import DEFAULT as D
from unittest.mock import Mock, call, patch

import pytest
import yaml
from pytest import fixture

from uwtools.drivers import jedi
from uwtools.scheduler import Slurm
from uwtools.tests.support import fixture_path, regex_logged

# Fixtures


@fixture
def cycle():
    return dt.datetime(2024, 2, 1, 18)


# Driver fixtures


@fixture
def config(tmp_path):
    return {
        "jedi": {
            "execution": {
                "batchargs": {
                    "export": "NONE",
                    "nodes": 1,
                    "stdout": "/path/to/file",
                    "walltime": "00:02:00",
                },
                "envcmds": [
                    "cmd1",
                    "cmd2",
                    "module load right-modules",
                    "module load jedi-modules",
                ],
                "executable": "/scratch2/BMC/zrtrr/Naureen.Bharwani/build/bin/qg_forecast.x",
                "mpiargs": ["--export=ALL", "--ntasks $SLURM_CPUS_ON_NODE"],
                "mpicmd": "srun",
            },
            "configuration_file": {
                "base_file": str(fixture_path("jedi.yaml")),
                "update_values": {"jedi": {}},
            },
            "files_to_copy": {"foo": "/path/to/foo", "bar/baz": "/path/to/baz"},
            "files_to_link": {"foo": "/path/to/foo", "bar/baz": "/path/to/baz"},
            "run_dir": "/path/to/run",
        },
        "platform": {
            "account": "me",
            "scheduler": "slurm",
        },
    }


@fixture
def config_file(config, tmp_path):
    path = tmp_path / "config.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f)
    return path


@fixture
def driverobj(config_file, cycle):
    return jedi.JEDI(config=config_file, cycle=cycle, batch=True)


# Driver tests


def test_JEDI(driverobj):
    assert isinstance(driverobj, jedi.JEDI)


def test_JEDI_dry_run(config_file, cycle):
    with patch.object(jedi, "dryrun") as dryrun:
        driverobj = jedi.JEDI(config=config_file, cycle=cycle, batch=True, dry_run=True)
    assert driverobj._dry_run is True
    dryrun.assert_called_once_with()


def test_JEDI_files_copied(caplog, driverobj):
    # logging.getLogger().setLevel(logging.INFO)
    with patch.object(jedi, "filecopy") as filecopy:
        driverobj.files_copied()
        assert filecopy.call_count == 2
        assert (
            call(src=Path("/path/to/baz"), dst=Path("/path/to/run/bar/baz"))
            in filecopy.call_args_list
        )
        assert (
            call(src=Path("/path/to/foo"), dst=Path("/path/to/run/foo")) in filecopy.call_args_list
        )


def test_JEDI_files_linked(caplog, driverobj):
    # logging.getLogger().setLevel(logging.INFO)
    with patch.object(jedi, "symlink") as symlink:
        driverobj.files_linked()
        assert symlink.call_count == 2
        assert (
            call(target=Path("/path/to/baz"), linkname=Path("/path/to/run/bar/baz"))
            in symlink.call_args_list
        )
        assert (
            call(target=Path("/path/to/foo"), linkname=Path("/path/to/run/foo"))
            in symlink.call_args_list
        )


def test_JEDI_provisioned_run_directory(driverobj):
    with patch.multiple(
        driverobj,
        files_copied=D,
        files_linked=D,
        runscript=D,
        yaml_file=D,
    ) as mocks:
        driverobj.provisioned_run_directory()
    for m in mocks:
        mocks[m].assert_called_once_with()


def test_JEDI_run_batch(driverobj):
    with patch.object(driverobj, "_run_via_batch_submission") as func:
        driverobj.run()
    func.assert_called_once_with()


def test_JEDI_run_local(driverobj):
    driverobj._batch = False
    with patch.object(driverobj, "_run_via_local_execution") as func:
        driverobj.run()
    func.assert_called_once_with()


def test_JEDI_runscript(driverobj):
    with patch.object(driverobj, "_runscript") as runscript:
        driverobj.runscript()
        runscript.assert_called_once()
        args = ("envcmds", "envvars", "execution", "scheduler")
        types = [list, dict, list, Slurm]
        assert [type(runscript.call_args.kwargs[x]) for x in args] == types


def test_JEDI_validate_only(caplog, config_file, cycle, driverobj):
    logging.getLogger().setLevel(logging.INFO)
    with patch.object(jedi, "run") as run:
        result = Mock(output="", success=True)
        run.return_value = result
        driverobj.validate_only()
        run.assert_called_once_with(
            "20240201 18Z jedi validate_only",
            "cmd1 && cmd2 && module load right-modules && module load jedi-modules && time /scratch2/BMC/zrtrr/Naureen.Bharwani/build/bin/qg_forecast.x --validate-only /scratch2/BMC/zrtrr/Naureen.Bharwani/uwtools/src/uwtools/tests/fixtures/jedi.yaml 2>&1",
        )
    assert regex_logged(caplog, "Config is valid")


def test_JEDI_yaml_file(driverobj):
    pass
    # src = driverobj._rundir / "input.yaml"


def test_JEDI__driver_config(driverobj):
    assert driverobj._driver_config == driverobj._config["jedi"]


def test_JEDI__runscript_path(driverobj):
    assert driverobj._runscript_path == driverobj._rundir / "runscript.jedi"


def test_JEDI__taskname(driverobj):
    assert driverobj._taskname("foo") == "20240201 18Z jedi foo"
