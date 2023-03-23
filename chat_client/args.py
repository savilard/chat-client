import configargparse


def get_args():
    """Gets arguments from command line."""
    parser = configargparse.ArgParser()
    parser.add_argument("--host", help="server host URL", default='minechat.dvmn.org', env_var='SERVER_HOST')
    parser.add_argument("--inport", type=int, help="port to read msgs", default=5000, env_var='PORT_IN')
    parser.add_argument("--outport", type=int, help="port to write msgs", default=5050, env_var='PORT_OUT')
    parser.add_argument("--history", help="file to save transcript to", default='history', env_var='HISTORY_FILE_PATH')
    parser.add_argument("--token", help="your toke", default=None, env_var='TOKEN')
    return parser.parse_args()
