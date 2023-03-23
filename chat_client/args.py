import argparse

import configargparse


def get_args() -> argparse.Namespace:
    """Gets arguments from command line.

    Returns:
        object: cli arguments
    """
    parser = configargparse.ArgParser(default_config_files=['settings.ini'])
    parser.add_argument('--host', help='server host URL', default='minechat.dvmn.org')
    parser.add_argument('--outport', type=int, help='port to read msgs', default=5000)
    parser.add_argument('--inport', type=int, help='port to write msgs', default=5050)
    parser.add_argument('--history', help='file to save transcript to', default='minechat.history')
    parser.add_argument('--token', help='your toke', default=None, env_var='TOKEN')
    return parser.parse_args()
