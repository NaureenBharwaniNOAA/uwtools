"""
An assets driver for ww3.
"""

from pathlib import Path

from iotaa import asset, task, tasks

from uwtools.api.template import render
from uwtools.drivers.driver import AssetsCycleBased
from uwtools.strings import STR
from uwtools.utils.tasks import file


class WaveWatchIII(AssetsCycleBased):
    """
    An assets driver for ww3.
    """

    # Workflow tasks

    @task
    def namelist_file(self):
        """
        Render the namelist from the template file.
        """
        fn = "ww3_shel.nml"
        yield self._taskname(fn)
        path = self._rundir / fn
        yield asset(path, path.is_file)
        template_file = Path(self._driver_config["namelist"]["template_file"])
        yield file(template_file)
        render(
            input_file=template_file,
            output_file=path,
            overrides=self._driver_config["namelist"]["template_values"],
        )

    @tasks
    def provisioned_rundir(self):
        """
        Run directory provisioned with all required content.
        """
        yield self._taskname("provisioned run directory")
        yield [
            self.namelist_file(),
            self.restart_directory(),
        ]

    @task
    def restart_directory(self):
        """
        The restart directory.
        """
        yield self._taskname("restart directory")
        path = self._rundir / "restart_wave"
        yield asset(path, path.is_dir)
        yield None
        path.mkdir(parents=True)

    # Private helper methods

    @property
    def _driver_name(self) -> str:
        """
        Returns the name of this driver.
        """
        return STR.ww3
