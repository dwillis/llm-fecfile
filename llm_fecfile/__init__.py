import llm

from .fec_api import register_cli_commands
from .fragments import fec_fragment_loader
from .tools import FEC


@llm.hookimpl
def register_fragment_loaders(register):
    register("fec", fec_fragment_loader)


@llm.hookimpl
def register_tools(register):
    register(FEC)


@llm.hookimpl
def register_commands(cli):
    register_cli_commands(cli)
